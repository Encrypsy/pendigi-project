from django.db.models import Q
from accounts.models import Users
from .models import Activity

def notify_admins(actor, message, action_type=Activity.ActionType.CONTENT_PENDING):
    admins = Users.objects.filter(
        Q(role="admin") | Q(is_superuser=True)
    ).distinct()

    for admin in admins:
        Activity.objects.create(
            recipient=admin,
            actor=actor,
            action_type=action_type,
            message=message[:255],
        )
