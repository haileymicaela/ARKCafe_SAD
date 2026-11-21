import json
from io import BytesIO
from unittest import mock
from urllib.error import HTTPError

from django.test import TestCase, override_settings

from accounts.models import User
from core.models import Department, NcrRecord, Project, Recipient
from notifications import messages, services
from notifications.textbee import TextBeeError, normalize_phone_number, send_sms


class SmsBase(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            "staff@example.com", "Staff User", "pass12345", role=User.STAFF
        )
        self.quality = Department.objects.create(department_name="Quality")
        self.site = Department.objects.create(department_name="Site")
        self.project = Project.objects.create(
            project_name="Tower A", client_name="ACME", project_code="PRJ-001"
        )
        self.recipient = Recipient.objects.create(
            name="Quality Lead", mobile_number="09171234567", department=self.quality
        )
        self.other_recipient = Recipient.objects.create(
            name="Site Lead", mobile_number="09189999999", department=self.site
        )
        self.ncr = NcrRecord.objects.create(
            project=self.project,
            department=self.quality,
            created_by=self.staff,
            reference_no="NCR-2026-0001",
            subject="Cracked weld on column C4",
            cause=NcrRecord.CAUSE_WORKMANSHIP,
        )


class MessageTests(SmsBase):
    def test_new_ncr_message_has_subject_cause_and_description(self):
        self.ncr.description = "Weld toe crack found during visual inspection"
        text = messages.ncr_created_message(self.ncr)
        self.assertIn("New NCR-2026-0001 (PRJ-001)", text)
        self.assertIn("Subject: Cracked weld on column C4", text)
        self.assertIn("Cause: Workmanship", text)
        self.assertIn("Description: Weld toe crack found during visual inspection", text)

    def test_in_progress_message_uses_remarks(self):
        self.ncr.status = NcrRecord.STATUS_IN_PROGRESS
        text = messages.ncr_status_message(self.ncr, "open", "in_progress", "Crew assigned")
        self.assertIn("is now In Progress", text)
        self.assertIn("Remarks: Crew assigned", text)
        self.assertNotIn("Resolution type", text)

    def test_resolved_message_uses_type_note_and_remarks(self):
        self.ncr.status = NcrRecord.STATUS_RESOLVED
        self.ncr.resolution_type = "replaced"
        self.ncr.resolution_note = "Column recast to spec"
        text = messages.ncr_status_message(
            self.ncr, "in_progress", "resolved", "Repaired and inspected"
        )
        self.assertIn("is now Resolved", text)
        self.assertIn("Resolution type: Replaced", text)
        self.assertIn("Resolution note: Column recast to spec", text)
        self.assertIn("Remarks: Repaired and inspected", text)

    def test_reopened_message_uses_remarks(self):
        self.ncr.status = NcrRecord.STATUS_OPEN
        text = messages.ncr_status_message(
            self.ncr, "resolved", "open", "Reopened (previous resolution: Closed). Defect returned"
        )
        self.assertIn("is now Open", text)
        self.assertIn("Defect returned", text)

    def test_long_text_is_truncated(self):
        self.ncr.subject = "A" * 1000
        self.assertLessEqual(len(messages.ncr_created_message(self.ncr)), messages.MAX_LENGTH)


class DispatchTests(SmsBase):
    def test_created_notifies_every_recipient_by_default(self):
        with mock.patch("notifications.services.send_sms") as sms:
            services.notify_ncr_created(self.ncr.pk)
        self.assertEqual(sms.call_count, 2)
        numbers = {call.args[0] for call in sms.call_args_list}
        self.assertEqual(numbers, {"+639171234567", "+639189999999"})
        self.assertIn("Cracked weld on column C4", sms.call_args_list[0].args[1])

    @override_settings(TEXTBEE_NOTIFY_ALL_RECIPIENTS=False)
    def test_department_only_setting(self):
        with mock.patch("notifications.services.send_sms") as sms:
            services.notify_ncr_created(self.ncr.pk)
        sms.assert_called_once()
        self.assertEqual(sms.call_args[0][0], "+639171234567")

    def test_status_change_is_sent(self):
        self.ncr.status = NcrRecord.STATUS_IN_PROGRESS
        self.ncr.save(update_fields=["status"])
        with mock.patch("notifications.services.send_sms") as sms:
            services.notify_ncr_status_changed(self.ncr.pk, "open", "in_progress", "Started")
        self.assertEqual(sms.call_count, 2)
        self.assertIn("Remarks: Started", sms.call_args_list[0].args[1])

    def test_sms_failure_is_contained(self):
        with mock.patch("notifications.services.send_sms", side_effect=TextBeeError("boom")):
            services.notify_ncr_created(self.ncr.pk)  # must not raise

    def test_missing_ncr_is_ignored(self):
        services.notify_ncr_created(999999)  # must not raise

    @override_settings(TEXTBEE_ENABLED=False)
    def test_disabled_skips_sms(self):
        with mock.patch("notifications.services.send_sms") as sms:
            services.notify_ncr_created(self.ncr.pk)
        sms.assert_not_called()


class NormalizeTests(TestCase):
    def test_philippine_formats(self):
        self.assertEqual(normalize_phone_number("09171234567"), "+639171234567")
        self.assertEqual(normalize_phone_number("639171234567"), "+639171234567")
        self.assertEqual(normalize_phone_number("+639171234567"), "+639171234567")
        self.assertEqual(normalize_phone_number("0917 123 4567"), "+639171234567")


class ClientTests(TestCase):
    @override_settings(
        TEXTBEE_ENABLED=True,
        TEXTBEE_DRY_RUN=False,
        TEXTBEE_API_KEY="test-key",
        TEXTBEE_DEVICE_ID="device-123",
        TEXTBEE_BASE_URL="https://api.textbee.dev/api/v1",
    )
    def test_request_payload_and_endpoint(self):
        response = mock.MagicMock()
        response.read.return_value = json.dumps(
            {"data": {"success": True, "smsBatchId": "batch-1", "recipientCount": 1}}
        ).encode()
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with mock.patch("notifications.textbee.urllib.request.urlopen", return_value=response) as urlopen:
            data = send_sms("09171234567", "Hello")

        self.assertEqual(data["smsBatchId"], "batch-1")
        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://api.textbee.dev/api/v1/gateway/send-sms")
        self.assertEqual(request.get_header("X-api-key"), "test-key")
        payload = json.loads(request.data)
        self.assertEqual(payload["recipients"], ["+639171234567"])
        self.assertEqual(payload["deviceId"], "device-123")

    @override_settings(TEXTBEE_ENABLED=True, TEXTBEE_DRY_RUN=False, TEXTBEE_API_KEY="bad-key")
    def test_api_error_is_raised_with_detail(self):
        error = HTTPError(
            "https://api.textbee.dev/api/v1/gateway/send-sms",
            401,
            "Unauthorized",
            {},
            BytesIO(json.dumps({"message": "API key rejected"}).encode()),
        )
        with mock.patch("notifications.textbee.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(TextBeeError) as ctx:
                send_sms("09171234567", "Hello")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("API key rejected", str(ctx.exception))

    @override_settings(TEXTBEE_ENABLED=True, TEXTBEE_DRY_RUN=False, TEXTBEE_API_KEY="bad-key")
    def test_api_error_reads_error_and_code_fields(self):
        error = HTTPError(
            "https://api.textbee.dev/api/v1/gateway/send-sms",
            401,
            "Unauthorized",
            {},
            BytesIO(json.dumps({"error": "Unauthorized", "code": "AUTH_INVALID"}).encode()),
        )
        with mock.patch("notifications.textbee.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(TextBeeError) as ctx:
                send_sms("09171234567", "Hello")
        self.assertIn("Unauthorized (AUTH_INVALID)", str(ctx.exception))

    @override_settings(TEXTBEE_ENABLED=True, TEXTBEE_DRY_RUN=True, TEXTBEE_API_KEY="test-key")
    def test_dry_run_does_not_call_api(self):
        with mock.patch("notifications.textbee.urllib.request.urlopen") as urlopen:
            data = send_sms("09171234567", "Hello")
        urlopen.assert_not_called()
        self.assertTrue(data["dryRun"])
