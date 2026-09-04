from django.db import models
from accounts.models import Users, StatusKontributor

class GenreFiksi(models.TextChoices):
    ROMANCE = 'romance', 'Romance'
    HORROR = 'horror', 'Horror'
    THRILLER = 'thriller', 'Thriller'
    MYSTERY = 'mystery', 'Mystery'
    SCIECE_FICTION = 'science_fiction', 'Science Fiction'
    COMEDY = 'comedy', 'Comedy'
    ADVENTURE = 'adventure', 'Adventure'
    DRAMA = 'drama', 'Drama'
    FANTASY = 'fantasy', 'Fantasy'

class TargetPembaca(models.TextChoices):
    UMUM = 'umum', 'Umum'
    REMAJA = 'remaja', 'Remaja'
    DEWASA = 'dewasa', 'Dewasa'

class StatusStory(models.TextChoices):
    PENDING = 'pending', 'Menunggu approval'
    APPROVED = 'approved', 'Disetujui'
    REJECTED = 'rejected', 'Ditolak'

class Stories(models.Model):
    author = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        limit_choices_to={
            'status_kontributor': StatusKontributor.APPROVED
        },
        related_name='stories'
    )
    title = models.CharField(max_length=150)
    cover = models.ImageField(
        upload_to='stories/covers/',
        null=True,
        blank=True
    )
    description = models.TextField()
    genre = models.CharField(
        max_length=20,
        choices=GenreFiksi.choices
    )
    tags = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Pisahkan tag dengan spasi"
    )
    target_pembaca = models.CharField(
        max_length=20, 
        choices=TargetPembaca.choices, 
        default=TargetPembaca.UMUM
    )
    status = models.CharField(
        max_length=20, 
        choices=StatusStory.choices, 
        default=StatusStory.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Stories"

    def __str__(self):
        return self.title

    def total_chapters(self):
        return self.chapters.count()

class Chapters(models.Model):
    story = models.ForeignKey(Stories, on_delete=models.CASCADE, related_name='chapters')
    chapter_number = models.PositiveIntegerField()
    title = models.CharField(max_length=150)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['chapter_number']
        constraints = [
            models.UniqueConstraint(fields=['story', 'chapter_number'], name='unique_story_chapter_number')
        ]

    def __str__(self):
        return f'{self.story.title} - Bab {self.chapter_number}: {self.title}'

    def word_count(self):
        return len(self.content.split())

