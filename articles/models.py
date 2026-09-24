from django.db import models
from accounts.models import Users, StatusKontributor


class StatusArticle(models.TextChoices):
    PENDING = "pending", "Menunggu approval"
    APPROVED = "approved", "Disetujui"
    REJECTED = "rejected", "Ditolak"


class Categories(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Articles(models.Model):
    title = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to='articles/thumbnails/', null=True, blank=True)
    content = models.TextField()
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='articles')
    contributor = models.ForeignKey(
        Users, on_delete=models.CASCADE,
        limit_choices_to={'status_kontributor': StatusKontributor.APPROVED},
        related_name='articles'
    )
    status = models.CharField(max_length=20, choices=StatusArticle.choices, default=StatusArticle.PENDING)
    views_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Banner(models.Model):
    title = models.CharField(max_length=100, blank=True, help_text="Opsional, judul yang muncul di overlay banner")
    image = models.ImageField(upload_to='banners/')
    link_url = models.CharField(max_length=255, blank=True, help_text="Opsional, arahkan ke URL tertentu saat banner diklik")
    order = models.PositiveIntegerField(default=0, help_text="Angka kecil tampil lebih dulu")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title or f'Banner #{self.pk}'