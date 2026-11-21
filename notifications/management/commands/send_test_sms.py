"""Send a test SMS to verify the TextBee configuration.

Usage:
    python manage.py send_test_sms 09171234567
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from notifications.textbee import TextBeeError, normalize_phone_number, send_sms


class Command(BaseCommand):
    help = "Send a test SMS through the configured TextBee device."

    def add_arguments(self, parser):
        parser.add_argument("number", help="Recipient mobile number (e.g. 09171234567)")
        parser.add_argument(
            "--message",
            default="ARK Cafe NCR test message. TextBee is configured correctly.",
        )

    def handle(self, *args, **options):
        if not settings.TEXTBEE_API_KEY:
            raise CommandError("TEXTBEE_API_KEY is not set in the environment.")

        number = normalize_phone_number(options["number"])
        self.stdout.write(f"Sending to {number} via {settings.TEXTBEE_BASE_URL} ...")
        try:
            data = send_sms(number, options["message"])
        except TextBeeError as exc:
            raise CommandError(f"TextBee error: {exc}") from exc

        if data.get("skipped"):
            self.stdout.write(self.style.WARNING("SMS skipped (TEXTBEE_ENABLED is off)."))
        elif data.get("dryRun"):
            self.stdout.write(self.style.WARNING("Dry run enabled; nothing was sent."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Queued batch {data.get('smsBatchId', '?')} "
                    f"for {data.get('recipientCount', 1)} recipient(s)."
                )
            )
