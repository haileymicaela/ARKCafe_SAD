"""Thin TextBee (textbee.dev) SMS API client.

Only the standard library is used, so this module needs no extra dependency.
Docs: https://textbee.dev/docs/sending-sms/sending-sms

Every call is made server-side; the API key never reaches the browser.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Iterable

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.textbee.dev/api/v1"


class TextBeeError(Exception):
    """Raised when TextBee rejects a request or cannot be reached."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def normalize_phone_number(number: str) -> str:
    """Return an E.164-style number, converting a local PH number if needed.

    ``09171234567`` -> ``+639171234567``
    ``639171234567`` -> ``+639171234567``
    ``+639171234567`` is returned unchanged.
    """
    cleaned = re.sub(r"[\s\-().]", "", str(number or ""))
    if cleaned.startswith("+"):
        return cleaned

    country_code = str(getattr(settings, "TEXTBEE_DEFAULT_COUNTRY_CODE", "63"))
    if cleaned.startswith("00"):
        return "+" + cleaned[2:]
    if cleaned.startswith(country_code) and len(cleaned) > len(country_code) + 6:
        return "+" + cleaned
    if cleaned.startswith("0"):
        return "+" + country_code + cleaned[1:]
    return "+" + country_code + cleaned


def mask_phone_number(number: str) -> str:
    """Keep phone numbers out of logs."""
    digits = re.sub(r"\D", "", number or "")
    return f"***{digits[-4:]}" if len(digits) >= 4 else "***"


def api_config() -> tuple[str, str, int]:
    """Return (api_key, base_url, timeout) from Django settings."""
    api_key = getattr(settings, "TEXTBEE_API_KEY", "") or ""
    base_url = (getattr(settings, "TEXTBEE_BASE_URL", "") or DEFAULT_BASE_URL).rstrip("/")
    timeout = getattr(settings, "TEXTBEE_TIMEOUT", 15)
    return api_key.strip(), base_url, timeout


def _error_detail(payload: dict, fallback: str) -> str:
    detail = payload.get("message") or payload.get("error") or ""
    code = payload.get("code")
    if code:
        detail = f"{detail} ({code})" if detail else str(code)
    return detail or fallback


def _request(path: str, *, method: str = "GET", payload: dict | None = None) -> dict:
    """Call the TextBee API and return the parsed JSON body."""
    api_key, base_url, timeout = api_config()
    if not api_key:
        raise TextBeeError("TEXTBEE_API_KEY is not set")

    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
            # urllib's default user agent is blocked by the API.
            "User-Agent": "ARKCafe-NCR/1.0",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = _error_detail(
                json.loads(exc.read().decode("utf-8") or "{}"),
                f"TextBee returned HTTP {exc.code}",
            )
        except (ValueError, OSError):
            detail = f"TextBee returned HTTP {exc.code}"
        raise TextBeeError(detail, exc.code) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TextBeeError(f"Could not reach TextBee: {exc}") from exc
    except ValueError as exc:  # invalid JSON response
        raise TextBeeError("TextBee returned an invalid response") from exc


def send_sms(
    recipients: Iterable[str] | str,
    message: str,
    *,
    device_id: str | None = None,
) -> dict:
    """Send one SMS batch through TextBee and return its ``data`` payload.

    Raises :class:`TextBeeError` on any failure. When SMS is disabled or the
    API key is not configured the message is logged and skipped.
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [normalize_phone_number(r) for r in recipients if str(r).strip()]
    if not recipients:
        raise TextBeeError("No recipients to send to")
    if not message or not message.strip():
        raise TextBeeError("Message is empty")

    if not getattr(settings, "TEXTBEE_ENABLED", True):
        logger.info("TextBee disabled; skipping SMS to %s", ", ".join(map(mask_phone_number, recipients)))
        return {"success": True, "skipped": True, "recipientCount": len(recipients)}

    api_key, _, _ = api_config()
    if not api_key:
        logger.warning("TEXTBEE_API_KEY is not set; SMS to %s was not sent", ", ".join(map(mask_phone_number, recipients)))
        return {"success": False, "skipped": True, "recipientCount": len(recipients)}

    if getattr(settings, "TEXTBEE_DRY_RUN", False):
        logger.info(
            "TextBee dry run -> %s: %s",
            ", ".join(map(mask_phone_number, recipients)),
            message,
        )
        return {"success": True, "dryRun": True, "recipientCount": len(recipients)}

    device_id = device_id or getattr(settings, "TEXTBEE_DEVICE_ID", "")
    payload = {"recipients": recipients, "message": message}
    if device_id:
        payload["deviceId"] = device_id

    body = _request("/gateway/send-sms", method="POST", payload=payload)
    data = body.get("data") or {}
    logger.info(
        "TextBee queued SMS batch %s for %d recipient(s)",
        data.get("smsBatchId", "?"),
        data.get("recipientCount", len(recipients)),
    )
    return data


def list_devices() -> list[dict]:
    """Return the devices on the TextBee account (used to verify the API key)."""
    body = _request("/gateway/devices")
    return body.get("data") or []
