from django.contrib import admin
from .models import Comments, Ratings, Bookmarks, StatusComment


@admin.action(description="Approve komentar terpilih")
def approve_comments(modeladmin, request, queryset):
    queryset.update(status=StatusComment.APPROVED)


@admin.action(description="Tolak komentar terpilih")
def reject_comments(modeladmin, request, queryset):
    queryset.update(status=StatusComment.REJECTED)


@admin.register(Comments)
class CommentsAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'status', 'created_at')
    list_filter = ('status',)
    actions = [approve_comments, reject_comments]


admin.site.register(Ratings)
admin.site.register(Bookmarks)