"""Verify the TextBee API key and show the phones on the account.

Usage:
    python manage.py check_textbee
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from notifications.textbee import TextBeeError, api_config, list_devices


class Command(BaseCommand):
    help = "Check the TextBee API key and list available sending devices."

    def handle(self, *args, **options):
        api_key, base_url, timeout = api_config()
        configured_device = getattr(settings, "TEXTBEE_DEVICE_ID", "")

        self.stdout.write(f"Base URL:  {base_url}")
        self.stdout.write(f"Timeout:   {timeout}s")
        self.stdout.write(f"Device ID: {configured_device or '(default device)'}")

        if not api_key:
            raise CommandError(
                "TEXTBEE_API_KEY is empty. Export it in the SAME terminal that runs "
                "manage.py, then restart the server."
            )

        self.stdout.write(f"API key:   {api_key[:4]}...{api_key[-4:]} ({len(api_key)} chars)")
        if api_key != api_key.strip() or api_key[:1] in {"'", '"'}:
            self.stdout.write(self.style.WARNING(
                "The key has surrounding spaces or quotes. Remove them."
            ))

        try:
            devices = list_devices()
        except TextBeeError as exc:
            raise CommandError(f"TextBee rejected the request: {exc}") from exc

        if not devices:
            self.stdout.write(self.style.WARNING(
                "The key works, but no devices are registered. Install the TextBee "
                "Android app and register a phone."
            ))
            return

        self.stdout.write(self.style.SUCCESS(f"API key is valid. {len(devices)} device(s):"))
        found_configured = False
        for device in devices:
            device_id = device.get("_id", "?")
            if device_id == configured_device:
                found_configured = True
            self.stdout.write(
                f"  - {device_id}  {device.get('name', '(unnamed)')}  "
                f"enabled={device.get('enabled')}  "
                f"default={device.get('isDefault', False)}  "
                f"lastHeartbeat={device.get('lastHeartbeat') or 'never'}"
            )

        if configured_device and not found_configured:
            self.stdout.write(self.style.WARNING(
                f"TEXTBEE_DEVICE_ID={configured_device} is not among the devices above. "
                "SMS will fail with 'Device not found'. Fix or remove it."
            ))
