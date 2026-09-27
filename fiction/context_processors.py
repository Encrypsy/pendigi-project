from .models import Stories, StatusStory


def fiction_navigation(request):
    all_tags_raw = (
        Stories.objects
        .filter(status=StatusStory.APPROVED)
        .exclude(tags='')
        .values_list('tags', flat=True)
    )

    unique_tags = set()

    for tag_string in all_tags_raw:
        for tag in tag_string.split():
            tag = tag.strip().lower()

            if tag:
                unique_tags.add(tag)

    return {
        'fiction_tags': sorted(unique_tags),
    }