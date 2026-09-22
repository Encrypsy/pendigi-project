from django.contrib.auth.models import AbstractUser
from django.db import models


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

    def __str__(self):
        return self.username


class ContributorApplication(models.Model):
    user = models.ForeignKey(
        Users, 
        on_delete=models.CASCADE, 
        related_name='contributor_applications'
    )
    bio = models.TextField(null=True, blank=True)
    portfolio_link = models.URLField()
    status = models.CharField(
        max_length=20, 
        choices=StatusKontributor.choices, 
        default=StatusKontributor.PENDING
    )
    admin_notes = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user.username} - {self.status}'

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