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

    def get_all_replies(self):
        """Ambil semua balasan secara flat, termasuk balasan dari balasan (rekursif)."""
        replies = []
        direct_replies = self.replies.filter(status=StatusComment.APPROVED).select_related('user', 'parent__user').order_by('created_at')
        for reply in direct_replies:
            replies.append(reply)
            replies.extend(reply.get_all_replies())
        return replies

    def __str__(self):
        return f'{self.user.username} ({self.article.title}) -- "{self.content[:30]}"'

    def total_likes(self):
        return self.likes.count()

    def total_dislikes(self):
        return self.dislikes.count()


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

class CommentLikes(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='comment_likes')
    comment = models.ForeignKey(Comments, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'comment'], name='unique_user_comment_like')]


class CommentDislikes(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='comment_dislikes')
    comment = models.ForeignKey(Comments, on_delete=models.CASCADE, related_name='dislikes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'comment'], name='unique_user_comment_dislike')]
        
class ArticleViewHistory(models.Model):
    article = models.ForeignKey(
        'articles.Articles',
        on_delete=models.CASCADE,
        related_name='view_history'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['viewed_at']

    def __str__(self):
        return f"{self.article.title} - {self.viewed_at}"
    
class Activity(models.Model):

    class ActionType(models.TextChoices):
        COMMENT = "comment", "Memberikan komentar"
        RATING = "rating", "Memberikan rating"
        APPROVED = "approved", "Konten disetujui"
        REJECTED = "rejected", "Konten ditolak"

    # User yang menerima notifikasi
    recipient = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name='received_activities'
    )

    # User yang melakukan aktivitas
    actor = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name='performed_activities',
        null=True,
        blank=True
    )

    # Konten yang berkaitan dengan aktivitas
    article = models.ForeignKey(
        Articles,
        on_delete=models.CASCADE,
        related_name='activities',
        null=True,
        blank=True
    )

    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices
    )

    # Bisa dipakai untuk menyimpan informasi tambahan
    # misalnya rating = 4
    message = models.CharField(
        max_length=255,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor = self.actor.username if self.actor else "System"

        return (
            f"{actor} - "
            f"{self.get_action_type_display()} - "
            f"{self.article.title if self.article else '-'}"
        )