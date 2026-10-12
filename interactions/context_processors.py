
def navbar_notifications(request):
    if not request.user.is_authenticated:
        return {
            'navbar_notifications': [],
            'navbar_unread_count': 0,
        }

    # Import model setelah Django siap memproses request
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
        'navbar_notifications': activities[:2],
        'navbar_unread_count': activities.filter(
            is_read=False
        ).count(),
    }
