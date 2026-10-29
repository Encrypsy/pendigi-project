
from django.db import transaction
from django.utils import timezone

from .models import ContributorApplication, StatusKontributor, Users
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

    newly_approved = (
        application.status != StatusKontributor.APPROVED
    )

    # Buat ID hanya jika user belum memilikinya.
    if not user.publisher_id:
        user.publisher_id = (
            f"PBL-{timezone.localdate().year}-{application.pk:06d}"
        )

    application.status = StatusKontributor.APPROVED
    application.save(update_fields=["status"])

    user.status_kontributor = StatusKontributor.APPROVED
    user.save(update_fields=["status_kontributor", "publisher_id"])

    # Kirim notifikasi hanya saat status baru berubah menjadi approved.
    if newly_approved:
        Activity.objects.create(
            recipient=user,
            actor=actor,
            action_type=Activity.ActionType.CONTRIBUTOR_APPROVED,
            message=(
                f"Pengajuan disetujui! "
                f"ID Publisher kamu: {user.publisher_id}"
            ),
        )

    return application


@transaction.atomic
def reject_contributor_application(application_id, actor=None):
    application = (
        ContributorApplication.objects
        .select_for_update()
        .get(pk=application_id)
    )

    user = Users.objects.select_for_update().get(
        pk=application.user_id
    )

    # Jangan mengubah pengajuan yang sudah disetujui.
    if application.status == StatusKontributor.APPROVED:
        return application

    newly_rejected = (
        application.status != StatusKontributor.REJECTED
    )

    application.status = StatusKontributor.REJECTED
    application.save(update_fields=["status"])

    user.status_kontributor = StatusKontributor.REJECTED
    user.save(update_fields=["status_kontributor"])

    if newly_rejected:
        Activity.objects.create(
            recipient=user,
            actor=actor,
            action_type=Activity.ActionType.CONTRIBUTOR_REJECTED,
            message=(
                "Pengajuan kontributor kamu ditolak. "
                "Silakan periksa catatan admin jika tersedia."
            ),
        )

    return application
