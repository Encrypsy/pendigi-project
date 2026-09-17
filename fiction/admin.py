from django.contrib import admin
from django.utils import timezone
from .models import Stories, Chapters, StatusStory


@admin.action(description="Approve cerita terpilih")
def approve_stories(modeladmin, request, queryset):
    queryset.update(status=StatusStory.APPROVED, published_at=timezone.now())


@admin.action(description="Tolak cerita terpilih")
def reject_stories(modeladmin, request, queryset):
    queryset.update(status=StatusStory.REJECTED)


@admin.register(Stories)
class StoriesAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'genre', 'status', 'total_chapters')
    list_filter = ('status', 'genre')
    actions = [approve_stories, reject_stories]


admin.site.register(Chapters)