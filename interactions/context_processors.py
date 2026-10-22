
def navbar_notifications(request):
    if not request.user.is_authenticated:
        return {
            'navbar_notifications': [],
            'navbar_unread_count': 0,
        }

    from .models import Activity

    activities = (
        Activity.objects
        .filter(recipient=request.user)
        .select_related(
            'actor',
            'article',
            'chapter',
            'chapter__story',
        )
        .order_by('-created_at')
    )

    return {
        'navbar_notifications': activities[:5],
        'navbar_unread_count': activities.filter(
            is_read=False
        ).count(),
    }


