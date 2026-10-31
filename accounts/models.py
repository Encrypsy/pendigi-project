from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    PEMBACA = "pembaca", "Pembaca"
    KONTRIBUTOR = "kontributor", "Kontributor"


class StatusKontributor(models.TextChoices):
    NONE = "none", "Belum daftar"
    PENDING = "pending", "Menunggu verifikasi"
    APPROVED = "approved", "Disetujui"
    REJECTED = "rejected", "Ditolak"


class Users(AbstractUser):
    role = models.CharField(
        max_length=20, 
        choices=Role.choices, 
        default=Role.PEMBACA
    )
    status_kontributor = models.CharField(
        max_length=20, 
        choices=StatusKontributor.choices, 
        default=StatusKontributor.NONE
    )
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.CharField(max_length=150, blank=True)
    banner_picture = models.ImageField(
        upload_to='profile_banners/',
        blank=True,
        null=True,
    )
    publisher_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name='ID Publisher',
    )

    def __str__(self):
        return self.username
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='unique_user_email_ci'
            ),
        ]
    
class ContributorApplication(models.Model):

    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name='contributor_applications',
    )

    # Data identitas
    nik = models.CharField(
        max_length=16,
        verbose_name='NIK',
    )

    full_name = models.CharField(
        max_length=150,
        verbose_name='Nama lengkap',
    )

    address = models.TextField(
        verbose_name='Alamat',
        blank=True,
        default='',
    )

    occupation = models.CharField(
        max_length=100,
        verbose_name='Pekerjaan',
        blank=True,
        default='',
    )

    email = models.EmailField(
        verbose_name='Email',
        blank=True,
        default='',
    )

    bio = models.TextField(
        verbose_name='Bio',
        blank=True,
        default='',
    )

    portfolio_link = models.URLField(
        verbose_name='Link portofolio',
        blank=True,
        default='',
    )

    # Moderasi pengajuan
    status = models.CharField(
        max_length=20,
        choices=StatusKontributor.choices,
        default=StatusKontributor.PENDING,
    )
    admin_notes = models.TextField(
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Pengajuan Kontributor'
        verbose_name_plural = 'Pengajuan Kontributor'

    def __str__(self):
        return f'{self.full_name} - {self.status}'

class Follow(models.Model):
    follower = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_follow_pair')
        ]

    def __str__(self):
        return f'{self.follower.username} follows {self.following.username}'
    

class ActionType(models.TextChoices):
    COMMENT = "comment", "Memberikan komentar"
    RATING = "rating", "Memberikan rating"
    APPROVED = "approved", "Konten disetujui"
    REJECTED = "rejected", "Konten ditolak"

    # Notifikasi untuk admin
    CONTRIBUTOR_APPLICATION = (
        "contributor_application",
        "Pengajuan kontributor",
    )
    CONTENT_PENDING = (
        "content_pending",
        "Konten menunggu moderasi",
    )

    # Notifikasi untuk pembaca
    FOLLOW = "follow", "Pengikut baru"
    LIKE = "like", "Konten disukai"
    COMMENT_REPLY = "comment_reply", "Balasan komentar"
    NEW_CHAPTER = "new_chapter", "Bab baru"
