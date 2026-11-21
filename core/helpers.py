from .models import ActivityLog


def log_activity(user, action_type, entity_type, entity_id,
                 entity_label="", old_value="", new_value=""):
    """Create a general activity feed entry for a successful user action."""
    if not getattr(user, "is_authenticated", False):
        return
    return ActivityLog.objects.create(
        user=user,
        action_type=str(action_type)[:30],
        entity_type=str(entity_type)[:30],
        entity_id=entity_id,
        entity_label=str(entity_label)[:150],
        old_value=str(old_value)[:255],
        new_value=str(new_value)[:255],
    )
