from django.contrib import admin
from .models import ReadingActivity, PersonalNotes, FavoriteArticles


@admin.register(ReadingActivity)
class ReadingActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'action_type', 'created_at')
    list_filter = ('action_type',)


admin.site.register(PersonalNotes)
admin.site.register(FavoriteArticles)