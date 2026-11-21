"""Integration points with the shared helpers (activity log + SMS).

The directions say log_activity and send_sms are shared helpers. When your
teammate adds them, change ONLY the two import lines below to the real module
and delete the temporary fallbacks.
"""
import logging

from core.helpers import log_activity
from core.models import Recipient

logger = logging.getLogger(__name__)

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
