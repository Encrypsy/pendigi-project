from django.contrib import admin
from django.utils import timezone
from .models import Categories, Articles, StatusArticle


@admin.action(description="Approve artikel terpilih")
def approve_articles(modeladmin, request, queryset):
    queryset.update(status=StatusArticle.APPROVED, published_at=timezone.now())


@admin.action(description="Tolak artikel terpilih")
def reject_articles(modeladmin, request, queryset):
    queryset.update(status=StatusArticle.REJECTED)


@admin.register(Articles)
class ArticlesAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'contributor', 'status', 'published_at')
    list_filter = ('status', 'category')
    actions = [approve_articles, reject_articles]


admin.site.register(Categories)