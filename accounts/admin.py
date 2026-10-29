from django.contrib import admin

from accounts.services import approve_contributor_application, reject_contributor_application
from .models import Users, ContributorApplication, StatusKontributor

@admin.action(description='Setujui pengajuan terpilih')
def approve_applications(modeladmin, request, queryset):
    for application in queryset:
        approve_contributor_application(
            application_id=application.pk,
            actor=request.user,
        )


@admin.action(description='Tolak pengajuan terpilih')
def reject_applications(modeladmin, request, queryset):
    for application in queryset:
        reject_contributor_application(
            application_id=application.pk,
            actor=request.user,
        )


@admin.register(ContributorApplication)
class ContributorApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'user',
        'email',
        'status',
        'submitted_at',
    )

    list_filter = ('status', 'gender', 'submitted_at')
    search_fields = (
        'full_name',
        'nik',
        'email',
        'user__username',
    )
    readonly_fields = ('submitted_at',)
    actions = [approve_applications, reject_applications]

    fieldsets = (
        ('Akun', {
            'fields': ('user', 'status', 'submitted_at'),
        }),
        ('Identitas pribadi', {
            'fields': (
                'nik',
                'full_name',
                'address',
                'occupation',
                'gender',
                'email',
            ),
        }),
        ('Profil penulis', {
            'fields': ('bio', 'portfolio_link'),
        }),
        ('Catatan admin', {
            'fields': ('admin_notes',),
        }),
    )


admin.site.register(Users)