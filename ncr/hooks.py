"""Integration points between NCR workflows and shared services.

NCR code names events and logs activity through this module; SMS wording and
delivery live in the ``notifications`` app.
"""

from core.helpers import log_activity  # noqa: F401  (used by ncr.views)
from notifications.services import (  # noqa: F401  (used by ncr.services)
    notify_ncr_created,
    notify_ncr_status_changed,
)

__all__ = ["log_activity", "notify_ncr_created", "notify_ncr_status_changed"]
