from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import Users
from articles.models import Articles


class StatusComment(models.TextChoices):
    PENDING = "pending", "Menunggu approval"
    APPROVED = "approved", "Disetujui"
    REJECTED = "rejected", "Ditolak"


class Comments(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='comments')
    article = models.ForeignKey(Articles, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies'
    )
    content = models.TextField()
    status = models.CharField(max_length=20, choices=StatusComment.choices, default=StatusComment.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} ({self.article.title}) -- "{self.content[:30]}"'


class Ratings(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='ratings')
    article = models.ForeignKey(Articles, on_delete=models.CASCADE, related_name='ratings')
    rating_value = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'article'], name='unique_user_article_rating')
        ]

    def __str__(self):
        return f'{self.user.username} -> {self.article.title} : {self.rating_value}'


class Bookmarks(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='bookmarks')
    article = models.ForeignKey(Articles, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'article'], name='unique_user_article_bookmark')
        ]

    def __str__(self):
        return f'{self.user.username} bookmarked {self.article.title}'