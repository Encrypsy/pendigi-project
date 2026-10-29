from django.contrib import admin
from .models import Users, ContributorApplication, StatusKontributor

@admin.action(description='Setujui pengajuan terpilih')
def approve_applications(modeladmin, request, queryset):
    for application in queryset:
        application.status = StatusKontributor.APPROVED
        application.save(update_fields=['status'])

        application.user.status_kontributor = StatusKontributor.APPROVED
        application.user.save(update_fields=['status_kontributor'])


@admin.action(description='Tolak pengajuan terpilih')
def reject_applications(modeladmin, request, queryset):
    for application in queryset:
        application.status = StatusKontributor.REJECTED
        application.save(update_fields=['status'])

        application.user.status_kontributor = StatusKontributor.REJECTED
        application.user.save(update_fields=['status_kontributor'])


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