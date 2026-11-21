"""NCR -> TextBee notification service.

Public functions are safe to call from request/transaction code: they never
raise, and they only look up the database after the surrounding transaction
has committed.
"""

from __future__ import annotations

import logging

from django.conf import settings

from core.models import NcrRecord, Recipient

from . import messages
from .textbee import TextBeeError, mask_phone_number, normalize_phone_number, send_sms

logger = logging.getLogger(__name__)


def recipients_for(ncr: NcrRecord):
    """Alert Recipients that should hear about this NCR.

    By default every recipient on the Alert Recipients page is notified,
    regardless of the NCR's department. Set
    ``TEXTBEE_NOTIFY_ALL_RECIPIENTS = False`` to limit alerts to the NCR's
    responsible department.
    """
    qs = Recipient.objects.all()
    if not getattr(settings, "TEXTBEE_NOTIFY_ALL_RECIPIENTS", True):
        qs = qs.filter(department_id=ncr.department_id)
    return qs.order_by("recipient_id")


def _send_to_all(ncr: NcrRecord, message: str) -> None:
    if not getattr(settings, "TEXTBEE_ENABLED", True):
        logger.info("SMS notifications disabled; skipped %s", ncr.reference_no)
        return

    numbers: list[str] = []
    for recipient in recipients_for(ncr):
        try:
            number = normalize_phone_number(recipient.mobile_number)
        except Exception:  # noqa: BLE001 - bad data must not break the request
            logger.exception("Invalid mobile number for recipient %s", recipient.pk)
            continue
        if number not in numbers:
            numbers.append(number)

    if not numbers:
        logger.info("No alert recipients for department %s (%s)", ncr.department_id, ncr.reference_no)
        return

    # Send one by one so a single bad number cannot reject the whole batch.
    for number in numbers:
        try:
            send_sms(number, message)
        except TextBeeError:
            logger.exception(
                "TextBee SMS failed for %s (%s)", ncr.reference_no, mask_phone_number(number)
            )
        except Exception:  # noqa: BLE001 - SMS must never break the workflow
            logger.exception(
                "Unexpected SMS error for %s (%s)", ncr.reference_no, mask_phone_number(number)
            )


def notify_ncr_created(ncr_id: int) -> None:
    """SMS the NCR's alert recipients with its subject and cause."""
    try:
        ncr = NcrRecord.objects.select_related("project", "department").get(pk=ncr_id)
    except NcrRecord.DoesNotExist:
        logger.warning("notify_ncr_created: NCR %s no longer exists", ncr_id)
        return

    _send_to_all(ncr, messages.ncr_created_message(ncr))


def notify_ncr_status_changed(
    ncr_id: int,
    old_status: str,
    new_status: str,
    remarks: str = "",
) -> None:
    """SMS the NCR's alert recipients about a status change."""
    try:
        ncr = NcrRecord.objects.select_related("project", "department").get(pk=ncr_id)
    except NcrRecord.DoesNotExist:
        logger.warning("notify_ncr_status_changed: NCR %s no longer exists", ncr_id)
        return

    _send_to_all(ncr, messages.ncr_status_message(ncr, old_status, new_status, remarks))
