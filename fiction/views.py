from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import StatusKontributor
from .models import Stories, Chapters, StatusStory, FavoriteStories
from .forms import StoryForm, ChapterForm
from django.http import JsonResponse
from accounts.decorators import admin_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import F

def tag_suggestions(request):
    query = request.GET.get('q', '').strip().lower()

    all_tags_raw = Stories.objects.exclude(tags='').values_list('tags', flat=True)
    unique_tags = set()
    for tag_string in all_tags_raw:
        for tag in tag_string.split():
            unique_tags.add(tag.lower())

    if query:
        matches = [t for t in unique_tags if t.startswith(query)]
    else:
        matches = list(unique_tags)

    return JsonResponse({'tags': sorted(matches)[:8]})


@login_required
def create_story(request):
    if request.user.status_kontributor != StatusKontributor.APPROVED:
        messages.error(request, 'Anda belum terverifikasi sebagai kontributor.')
        return redirect('articles:article_list')

    if request.method == 'POST':
        form = StoryForm(request.POST, request.FILES)
        if form.is_valid():
            story = form.save(commit=False)
            story.author = request.user
            story.save()
            messages.success(request, 'Detail cerita tersimpan. Sekarang tambahkan bab pertamamu!')
            return redirect('fiction:chapter_list', story_id=story.pk)
    else:
        form = StoryForm()

    return render(request, 'fiction/story_form.html', {'form': form, 'is_edit': False})


@login_required
def edit_story(request, pk):
    story = get_object_or_404(Stories, pk=pk, author=request.user)

    if request.method == 'POST':
        form = StoryForm(request.POST, request.FILES, instance=story)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.status = StatusStory.PENDING
            updated.published_at = None
            updated.save()
            messages.success(request, 'Detail cerita diperbarui, menunggu approval ulang.')
            return redirect('fiction:my_stories')
    else:
        form = StoryForm(instance=story)

    return render(request, 'fiction/story_form.html', {'form': form, 'is_edit': True, 'story': story})


@login_required
def my_stories(request):
    stories = Stories.objects.filter(author=request.user)
    return render(request, 'fiction/my_stories.html', {'stories': stories})


@login_required
def chapter_list(request, story_id):
    story = get_object_or_404(Stories, pk=story_id, author=request.user)
    chapters = story.chapters.all()
    return render(request, 'fiction/chapter_list.html', {'story': story, 'chapters': chapters})


@login_required
def add_chapter(request, story_id):
    story = get_object_or_404(Stories, pk=story_id, author=request.user)
    next_number = story.chapters.count() + 1

    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.story = story
            chapter.chapter_number = next_number
            chapter.save()
            messages.success(request, f'Bab {next_number} berhasil disimpan.')
            return redirect('fiction:chapter_list', story_id=story.pk)
    else:
        form = ChapterForm()

    return render(request, 'fiction/chapter_form.html', {
        'form': form, 'story': story, 'chapter_number': next_number, 'is_edit': False
    })


@login_required
def edit_chapter(request, story_id, chapter_id):
    story = get_object_or_404(Stories, pk=story_id, author=request.user)
    chapter = get_object_or_404(Chapters, pk=chapter_id, story=story)

    if request.method == 'POST':
        form = ChapterForm(request.POST, instance=chapter)
        if form.is_valid():
            form.save()
            messages.success(request, f'Bab {chapter.chapter_number} berhasil diperbarui.')
            return redirect('fiction:chapter_list', story_id=story.pk)
    else:
        form = ChapterForm(instance=chapter)

    return render(request, 'fiction/chapter_form.html', {
        'form': form, 'story': story, 'chapter_number': chapter.chapter_number, 'is_edit': True
    })


@login_required
def delete_chapter(request, story_id, chapter_id):
    story = get_object_or_404(Stories, pk=story_id, author=request.user)
    chapter = get_object_or_404(Chapters, pk=chapter_id, story=story)
    chapter.delete()
    messages.success(request, 'Bab berhasil dihapus.')
    return redirect('fiction:chapter_list', story_id=story.pk)

@admin_required
def admin_pending_stories(request):
    stories = Stories.objects.filter(status=StatusStory.PENDING).select_related('author')
    return render(request, 'fiction/admin_pending.html', {'stories': stories})


@admin_required
@require_POST
def admin_approve_story(request, pk):
    story = get_object_or_404(Stories, pk=pk)
    story.status = StatusStory.APPROVED
    story.published_at = timezone.now()
    story.save()
    messages.success(request, f'Cerita "{story.title}" disetujui.')
    return redirect('fiction:admin_pending_stories')


@admin_required
@require_POST
def admin_reject_story(request, pk):
    story = get_object_or_404(Stories, pk=pk)
    story.status = StatusStory.REJECTED
    story.save()
    messages.success(request, f'Cerita "{story.title}" ditolak.')
    return redirect('fiction:admin_pending_stories')

@admin_required
def admin_review_story(request, pk):
    story = get_object_or_404(Stories, pk=pk)
    chapters = story.chapters.all()
    return render(request, 'fiction/admin_review.html', {'story': story, 'chapters': chapters})

def story_list(request):
    stories = Stories.objects.filter(status=StatusStory.APPROVED).select_related('author')
    return render(request, 'fiction/story_list.html', {'stories': stories})


def story_detail(request, pk):
    story = get_object_or_404(Stories, pk=pk, status=StatusStory.APPROVED)

    Stories.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    story.refresh_from_db(fields=['views_count'])

    chapters = story.chapters.all()
    similar_stories = story.get_similar_stories()

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = FavoriteStories.objects.filter(user=request.user, story=story).exists()

    return render(request, 'fiction/story_detail.html', {
        'story': story,
        'chapters': chapters,
        'is_favorited': is_favorited,
        'similar_stories': similar_stories,
    })


def read_chapter(request, pk, chapter_number):
    story = get_object_or_404(Stories, pk=pk, status=StatusStory.APPROVED)
    chapter = get_object_or_404(Chapters, story=story, chapter_number=chapter_number)

    Chapters.objects.filter(pk=chapter.pk).update(views_count=F('views_count') + 1)
    chapter.refresh_from_db(fields=['views_count'])

    all_chapters = story.chapters.all()
    prev_chapter = story.chapters.filter(chapter_number__lt=chapter_number).order_by('-chapter_number').first()
    next_chapter = story.chapters.filter(chapter_number__gt=chapter_number).order_by('chapter_number').first()

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = FavoriteStories.objects.filter(user=request.user, story=story).exists()

    return render(request, 'fiction/read_chapter.html', {
        'story': story,
        'chapter': chapter,
        'all_chapters': all_chapters,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'is_favorited': is_favorited,
    })

@login_required
@require_POST
def toggle_favorite_story(request, pk):
    story = get_object_or_404(Stories, pk=pk, status=StatusStory.APPROVED)
    favorite, created = FavoriteStories.objects.get_or_create(user=request.user, story=story)

    if not created:
        favorite.delete()
        messages.info(request, 'Dihapus dari favorit.')
    else:
        messages.success(request, 'Ditambahkan ke favorit.')

    return redirect('fiction:story_detail', pk=pk)

def tag_stories(request, tag):
    stories = Stories.objects.filter(status=StatusStory.APPROVED, tags__icontains=tag)
    stories = [s for s in stories if tag.lower() in [t.lower() for t in s.tag_list()]]
    return render(request, 'fiction/tag_stories.html', {'stories': stories, 'tag': tag})