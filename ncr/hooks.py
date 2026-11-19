"""Integration points with the shared helpers (activity log + SMS).

The directions say log_activity and send_sms are shared helpers. When your
teammate adds them, change ONLY the two import lines below to the real module
and delete the temporary fallbacks.
"""
import logging

from core.models import ActivityLog, Recipient

logger = logging.getLogger(__name__)

try:
    from core.helpers import log_activity  # noqa: F401  <- adjust module path
except ImportError:  # TEMPORARY fallback until the shared helper exists
    def log_activity(user, action_type, entity_type, entity_id,
                     entity_label="", old_value="", new_value=""):
        ActivityLog.objects.create(
            user=user,
            action_type=action_type[:30],
            entity_type=entity_type[:30],
            entity_id=entity_id,
            entity_label=entity_label[:150],
            old_value=old_value[:255],
            new_value=new_value[:255],
        )

# --- SMS TEMPORARILY DISABLED FOR PART 1 (NCR) ---
# try:
#     from core.helpers import send_sms  # noqa: F401  <- adjust module path
# except ImportError:  # TEMPORARY fallback until the shared helper exists
def send_sms(mobile_number, message):
    # logger.info("[SMS placeholder] to=%s message=%s", mobile_number, message)
    pass


def notify_department(ncr, message):
    """SMS every recipient of the NCR's department. Never breaks the request."""
    # --- SMS TEMPORARILY DISABLED ---
    # for recipient in Recipient.objects.filter(department=ncr.department):
    #     try:
    #         send_sms(recipient.mobile_number, message)
    #     except Exception:  # noqa: BLE001
    #         logger.exception("SMS to %s failed", recipient.mobile_number)
    pass