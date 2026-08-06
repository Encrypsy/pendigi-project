from django.contrib import admin
from .models import Users, ContributorApplication, StatusKontributor


@admin.action(description="Approve pengajuan terpilih")
def approve_applications(modeladmin, request, queryset):
    for application in queryset:
        application.status = StatusKontributor.APPROVED
        application.save()

        application.user.status_kontributor = StatusKontributor.APPROVED
        application.user.save()


@admin.action(description="Tolak pengajuan terpilih")
def reject_applications(modeladmin, request, queryset):
    for application in queryset:
        application.status = StatusKontributor.REJECTED
        application.save()

        application.user.status_kontributor = StatusKontributor.REJECTED
        application.user.save()


@admin.register(ContributorApplication)
class ContributorApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'submitted_at')
    list_filter = ('status',)
    actions = [approve_applications, reject_applications]


admin.site.register(Users)