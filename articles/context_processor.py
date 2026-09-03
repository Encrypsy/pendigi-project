from .models import Categories


def navbar_categories(request):
    return {
        'navbar_categories': Categories.objects.all().order_by('name')
    }