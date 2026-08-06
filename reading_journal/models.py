from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import Users
from articles.models import Articles


class ActionType(models.TextChoices):
    STARTED_READING = "started_reading", "Mulai membaca"
    FINISHED_READING = "finished_reading", "Selesai membaca"
    RATED = "rated", "Memberi rating"
    COMMENTED = "commented", "Menulis komentar"
    BOOKMARKED = "bookmarked", "Menyimpan artikel"


class ReadingActivity(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='activities')
    article = models.ForeignKey(Articles, on_delete=models.CASCADE, related_name='activities')
    action_type = models.CharField(max_length=30, choices=ActionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Reading activities"

    def __str__(self):
        return f'{self.user.username} - {self.action_type} - {self.article.title}'


class PersonalNotes(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='personal_notes')
    article = models.ForeignKey(Articles, on_delete=models.CASCADE, related_name='personal_notes')
    note_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Catatan {self.user.username} di {self.article.title}'


class FavoriteArticles(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='favorite_articles')
    article = models.ForeignKey(Articles, on_delete=models.CASCADE, related_name='favorited_by')
    rank_order = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])

    class Meta:
        ordering = ['rank_order']
        constraints = [
            models.UniqueConstraint(fields=['user', 'rank_order'], name='unique_user_rank_order'),
            models.UniqueConstraint(fields=['user', 'article'], name='unique_user_favorite_article'),
        ]

    def __str__(self):
        return f'{self.user.username} - #{self.rank_order} - {self.article.title}'