
from django.db import transaction
from django.utils import timezone

from .models import ContributorApplication, Role, StatusKontributor, Users
from interactions.models import Activity

@transaction.atomic
def approve_contributor_application(application_id, actor=None):
    application = (
        ContributorApplication.objects
        .select_for_update()
        .get(pk=application_id)
    )

    user = Users.objects.select_for_update().get(
        pk=application.user_id
    )

    # Jika sudah disetujui, jangan membuat notifikasi duplikat.
    if application.status == StatusKontributor.APPROVED:
        return application

    # Buat ID Publisher jika belum ada.
    if not user.publisher_id:
        user.publisher_id = (
            f"PBL-{timezone.localdate().year}-{application.pk:06d}"
        )

    # Perbarui status pengajuan.
    application.status = StatusKontributor.APPROVED
    application.save(update_fields=["status"])

    # Perbarui role dan status kontributor.
    user.role = Role.KONTRIBUTOR
    user.status_kontributor = StatusKontributor.APPROVED
    user.save(
        update_fields=[
            "role",
            "status_kontributor",
            "publisher_id",
        ]
    )

    # Kirim notifikasi persetujuan beserta ID Publisher.
    Activity.objects.create(
        recipient=user,
        actor=actor,
        action_type=Activity.ActionType.CONTRIBUTOR_APPROVED,
        message=(
            "Pengajuan kontributor kamu disetujui! "
            f"ID Publisher kamu: {user.publisher_id}"
        ),
    )

    return application

@transaction.atomic
def reject_contributor_application(
    application_id,
    actor=None,
    admin_notes=None,
):
    application = (
        ContributorApplication.objects
        .select_for_update()
        .get(pk=application_id)
    )

    user = Users.objects.select_for_update().get(
        pk=application.user_id
    )

    # Pengajuan yang sudah disetujui tidak boleh ditolak.
    if application.status == StatusKontributor.APPROVED:
        return application

    # Hindari notifikasi penolakan berulang.
    if application.status == StatusKontributor.REJECTED:
        return application

    admin_notes = (admin_notes or '').strip()

    if not admin_notes:
        raise ValueError('Alasan penolakan wajib diisi.')

    application.status = StatusKontributor.REJECTED
    application.admin_notes = admin_notes
    application.save(
        update_fields=['status', 'admin_notes']
    )

    user.status_kontributor = StatusKontributor.REJECTED
    user.save(update_fields=['status_kontributor'])

    Activity.objects.create(
        recipient=user,
        actor=actor,
        action_type=Activity.ActionType.CONTRIBUTOR_REJECTED,
        message=(
            'Pengajuan kontributor kamu ditolak. '
            'Silakan periksa catatan admin untuk mengetahui alasannya.'
        ),
    )

    return application
