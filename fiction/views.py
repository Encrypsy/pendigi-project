from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from accounts.models import StatusKontributor, Follow
from articles.models import Banner, BannerType
from interactions.models import StatusComment, Activity
from interactions.notifications import notify_admins
from .models import StatusChapter, Stories, Chapters, StatusStory, FavoriteStories, ChapterComments, ChapterCommentLikes, ReadingProgress
from .forms import StoryForm, ChapterForm, ChapterCommentForm
from django.http import JsonResponse
from accounts.decorators import admin_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import F, Count, Q
from django.http import JsonResponse

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
            
            notify_admins(
                actor=request.user,
                message=f"Cerita '{story.title}' menunggu moderasi.",
                action_type=Activity.ActionType.CONTENT_PENDING,
            )
            
            messages.success(request, 'Detail cerita tersimpan. Sekarang tambahkan bab pertamamu!')
            return redirect('fiction:chapter_list', story_id=story.pk)
    else:
        form = StoryForm()

    return render(request, 'fiction/story_form.html', {
        'form': form,
        'is_edit': False,
        'active_menu': 'create_content',
        'active_create_type': 'fiction',
        'breadcrumb': 'Buat Konten / Fiksi',
    })


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
            
            notify_admins(
                actor=request.user,
                message=f'Cerita "{updated.title}" menunggu moderasi ulang.',
                action_type=Activity.ActionType.CONTENT_PENDING,
            )
            
            messages.success(request, 'Detail cerita diperbarui, menunggu approval ulang.')
            return redirect('fiction:my_stories')
    else:
        form = StoryForm(instance=story)

    return render(request, 'fiction/story_form.html', {
        'form': form,
        'is_edit': True,
        'story': story,
        'active_menu': 'create_content',
        'active_create_type': 'fiction',
        'breadcrumb': 'Buat Konten / Fiksi',
    })

@login_required
@require_POST
def delete_story(request, pk):
    story = get_object_or_404(
        Stories,
        pk=pk,
        author=request.user
    )

    story.delete()

    messages.success(request, 'Cerita berhasil dihapus.')
    return redirect('fiction:my_stories')

@login_required
def my_stories(request):
    stories = Stories.objects.filter(author=request.user)
    return render(request, 'fiction/my_stories.html', {'stories': stories})


@login_required
def chapter_list(request, story_id):
    story = get_object_or_404(Stories, pk=story_id, author=request.user)
    chapters = Chapters.objects.filter(
        story=story,
        status=StatusChapter.APPROVED
    ).order_by('chapter_number')
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
            
            notify_admins(
                actor=request.user,
                message=(
                    f"Bab '{chapter.title}' dari cerita "
                    f"'{story.title}' menunggu moderasi."
                ),
                action_type=Activity.ActionType.CONTENT_PENDING,
            )
            
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
    stories = (
        Stories.objects
        .filter(chapters__status=StatusChapter.PENDING)
        .select_related('author')
        .annotate(
            total_pending_chapters=Count(
                'chapters',
                filter=Q(chapters__status=StatusChapter.PENDING),
                distinct=True,
            )
        )
        .distinct()
        .order_by('-created_at')
    )

    return render(request, 'fiction/admin_pending.html', {
        'stories': stories,
        'breadcrumb': 'Fiksi Pending',
        'active_menu': 'approval',
    })


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
def admin_approve_chapter(request, story_id, chapter_id):
    story = get_object_or_404(Stories, pk=story_id)
    chapter = get_object_or_404(
        Chapters,
        pk=chapter_id,
        story=story,
    )

    chapter.status = StatusChapter.APPROVED
    chapter.rejection_reason = ''
    chapter.save(update_fields=['status', 'rejection_reason'])
    
    Activity.objects.create(
        recipient=story.author,
        actor=request.user,
        chapter=chapter,
        action_type=Activity.ActionType.APPROVED,
        message=(
            f'Admin telah menyetujui cerita "{story.title}", '
            f'Bab {chapter.chapter_number}: {chapter.title}.'
        ),
    )

    messages.success(
        request,
        f'Bab {chapter.chapter_number} berhasil disetujui.'
    )

    return redirect(
        f"{reverse('fiction:admin_review_story', args=[story.pk])}?bab={chapter.pk}"
    )


@admin_required
@require_POST
def admin_reject_chapter(request, story_id, chapter_id):
    story = get_object_or_404(Stories, pk=story_id)
    chapter = get_object_or_404(
        Chapters,
        pk=chapter_id,
        story=story,
    )

    chapter.status = StatusChapter.REJECTED
    chapter.rejection_reason = request.POST.get(
        'rejection_reason', ''
    ).strip()
    chapter.save(update_fields=['status', 'rejection_reason'])
    
    Activity.objects.create(
        recipient=story.author,
        actor=request.user,
        chapter=chapter,
        action_type=Activity.ActionType.REJECTED,
        message=(
            f'Admin telah menolak cerita "{story.title}", '
            f'Bab {chapter.chapter_number}: {chapter.title}. '
            f'Alasan: {chapter.rejection_reason or "Tidak ada alasan yang dicantumkan."}'
        ),
    )

    messages.warning(
        request,
        f'Bab {chapter.chapter_number} ditolak.'
    )

    return redirect(
        f"{reverse('fiction:admin_review_story', args=[story.pk])}?bab={chapter.pk}"
    )


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

    chapter_id = request.GET.get('bab')
    current_chapter = None

    if chapters.exists():
        if chapter_id:
            current_chapter = get_object_or_404(
                chapters,
                pk=chapter_id
            )
        else:
            current_chapter = chapters.first()

    chapter_list = list(chapters)

    current_index = None
    previous_chapter = None
    next_chapter = None

    if current_chapter:
        current_index = chapter_list.index(current_chapter)

        if current_index > 0:
            previous_chapter = chapter_list[current_index - 1]

        if current_index < len(chapter_list) - 1:
            next_chapter = chapter_list[current_index + 1]

    return render(request, 'fiction/admin_review.html', {
        'story': story,
        'chapters': chapters,
        'current_chapter': current_chapter,
        'current_index': current_index,
        'previous_chapter': previous_chapter,
        'next_chapter': next_chapter,
        'breadcrumb': 'Review Fiksi',
        'active_menu': 'approval',
    })

def story_list(request):
    # Hanya cerita yang sudah disetujui
    stories = Stories.objects.filter(
        status=StatusStory.APPROVED
    ).select_related('author')

    # SEARCH: judul, username penulis, atau tag
    search_query = request.GET.get('q', '').strip()

    if search_query:
        stories = stories.filter(
            Q(title__icontains=search_query)
            | Q(author__username__icontains=search_query)
            | Q(tags__icontains=search_query)
        )

    # FILTER KATEGORI
    genre_choices = Stories._meta.get_field('genre').choices
    selected_genre = request.GET.get('genre', '').strip()

    valid_genres = {
        str(value) for value, label in genre_choices
    }

    if selected_genre in valid_genres:
        stories = stories.filter(genre=selected_genre)
    else:
        selected_genre = ''

    # Banner fiksi tetap seperti sebelumnya
    banners = Banner.objects.filter(
        type=BannerType.FIKSI,
        is_active=True
    ).order_by('order', '-created_at')

    # Rekomendasi mengikuti pencarian dan kategori aktif
    recommended_stories = stories[:12]

    # TAG POPULER dari cerita yang telah disetujui
    all_tags = (
        Stories.objects
        .filter(status=StatusStory.APPROVED)
        .exclude(tags='')
        .values_list('tags', flat=True)
    )

    tag_counts = {}

    for tag_string in all_tags:
        for tag in tag_string.split():
            normalized_tag = tag.lstrip('#').strip()

            if not normalized_tag:
                continue

            key = normalized_tag.casefold()

            if key not in tag_counts:
                tag_counts[key] = {
                    'name': normalized_tag,
                    'count': 0,
                }

            tag_counts[key]['count'] += 1

    popular_tags = sorted(
        tag_counts.values(),
        key=lambda item: (-item['count'], item['name'].lower())
    )[:12]

    # LANJUTKAN MEMBACA: logika lama dipertahankan
    continue_reading = []

    if request.user.is_authenticated:
        progress_list = (
            ReadingProgress.objects
            .filter(
                user=request.user,
                last_chapter_number__gt=0,
                story__status=StatusStory.APPROVED,
            )
            .select_related(
                'story',
                'story__author'
            )
            .order_by('-updated_at')
        )

        for progress in progress_list:
            total_chapters = progress.total_chapters

            if total_chapters == 0:
                continue

            if progress.last_chapter_number >= total_chapters:
                continue

            continue_reading.append(progress)

            if len(continue_reading) >= 3:
                break

    return render(
        request,
        'fiction/story_list.html',
        {
            'stories': stories,
            'banners': banners,
            'recommended_stories': recommended_stories,
            'continue_reading': continue_reading[:2],
            'continue_reading_count': len(continue_reading),

            # Data search dan kategori
            'search_query': search_query,
            'genres': [
                {'value': value, 'label': label}
                for value, label in genre_choices
            ],
            'selected_genre': selected_genre,

            # Data tag
            'popular_tags': popular_tags,
        }
    )

def story_detail(request, pk):
    story = get_object_or_404(Stories, pk=pk, status=StatusStory.APPROVED)

    Stories.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    story.refresh_from_db(fields=['views_count'])

    chapters = story.chapters.filter(
        status=StatusChapter.APPROVED
    ).order_by('chapter_number')
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
    story = get_object_or_404(
        Stories,
        pk=pk,
        status=StatusStory.APPROVED,
    )

    chapter = get_object_or_404(
        Chapters,
        story=story,
        chapter_number=chapter_number,
        status=StatusChapter.APPROVED,
    )

    if request.user.is_authenticated:
        ReadingProgress.objects.update_or_create(
            user=request.user,
            story=story,
            defaults={
                'last_chapter_number': chapter_number,
            },
        )

    Chapters.objects.filter(pk=chapter.pk).update(
        views_count=F('views_count') + 1
    )
    chapter.refresh_from_db(fields=['views_count'])

    # Hanya bab yang sudah disetujui yang masuk navigasi publik.
    all_chapters = story.chapters.filter(
        status=StatusChapter.APPROVED
    ).order_by('chapter_number')

    prev_chapter = all_chapters.filter(
        chapter_number__lt=chapter_number
    ).order_by('-chapter_number').first()

    next_chapter = all_chapters.filter(
        chapter_number__gt=chapter_number
    ).order_by('chapter_number').first()

    from interactions.views import _attach_comment_meta

    comments_qs = (
        chapter.comments
        .filter(
            status=StatusComment.APPROVED,
            parent__isnull=True,
        )
        .select_related('user')
        .order_by('-created_at')
    )

    post_url = reverse(
        'fiction:submit_chapter_comment',
        kwargs={
            'pk': pk,
            'chapter_number': chapter_number,
        },
    )

    comments = _attach_comment_meta(
        comments_qs,
        request,
        'fiction:toggle_chapter_comment_like',
        'fiction:toggle_chapter_comment_like',
        url_kwargs={},
        post_url=post_url,
    )

    is_favorited = False
    is_following_author = False

    if request.user.is_authenticated:
        is_favorited = FavoriteStories.objects.filter(
            user=request.user,
            story=story,
        ).exists()

        is_following_author = Follow.objects.filter(
            follower=request.user,
            following=story.author,
        ).exists()

    return render(request, 'fiction/read_chapter.html', {
        'story': story,
        'chapter': chapter,
        'all_chapters': all_chapters,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'is_favorited': is_favorited,
        'is_following_author': is_following_author,
        'comments': comments,
        'total_count': chapter.comments.filter(
            status=StatusComment.APPROVED
        ).count(),
        'current_sort': 'recent',
        'post_url': post_url,
        'refresh_url': reverse(
            'fiction:chapter_comments_partial',
            kwargs={
                'pk': pk,
                'chapter_number': chapter_number,
            },
        ),
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

@login_required
@require_POST
def submit_chapter_comment(request, pk, chapter_number):
    story = get_object_or_404(Stories, pk=pk, status=StatusStory.APPROVED)
    chapter = get_object_or_404(Chapters, story=story, chapter_number=chapter_number)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    edit_id = request.POST.get('edit_id')
    if edit_id:
        comment = get_object_or_404(ChapterComments, pk=edit_id, user=request.user)
        comment.content = request.POST.get('content', comment.content)
        comment.save()
        if is_ajax:
            return JsonResponse({'ok': True})
        return redirect('fiction:read_chapter', pk=pk, chapter_number=chapter_number)

    form = ChapterCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.chapter = chapter

        parent_id = request.POST.get('parent_id')
        if parent_id:
            parent_comment = get_object_or_404(ChapterComments, pk=parent_id, chapter=chapter)
            comment.parent = parent_comment

        if request.user.role == 'admin' or request.user.is_superuser:
            comment.status = StatusComment.APPROVED

        comment.save()

        if is_ajax:
            return JsonResponse({'ok': True})
        messages.success(request, 'Komentar terkirim.')
    else:
        if is_ajax:
            return JsonResponse({'error': 'Komentar tidak boleh kosong.'})
        messages.error(request, 'Komentar tidak boleh kosong.')

    return redirect('fiction:read_chapter', pk=pk, chapter_number=chapter_number)


@login_required
@require_POST
def toggle_chapter_comment_like(request, comment_id):
    comment = get_object_or_404(ChapterComments, pk=comment_id)
    like, created = ChapterCommentLikes.objects.get_or_create(user=request.user, comment=comment)

    if not created:
        like.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('fiction:read_chapter', pk=comment.chapter.story.pk, chapter_number=comment.chapter.chapter_number)

def chapter_comments_partial(request, pk, chapter_number):
    story = get_object_or_404(Stories, pk=pk, status=StatusStory.APPROVED)
    chapter = get_object_or_404(Chapters, story=story, chapter_number=chapter_number)

    sort = request.GET.get('sort', 'recent')
    comments_qs = chapter.comments.filter(status=StatusComment.APPROVED, parent__isnull=True).select_related('user')

    if sort == 'oldest':
        comments_qs = comments_qs.order_by('created_at')
    elif sort == 'liked':
        comments_qs = sorted(comments_qs, key=lambda c: c.likes.count(), reverse=True)
    else:
        comments_qs = comments_qs.order_by('-created_at')

    from interactions.views import _attach_comment_meta

    post_url = reverse('fiction:submit_chapter_comment', kwargs={'pk': pk, 'chapter_number': chapter_number})
    comments = _attach_comment_meta(
        comments_qs, request,
        'fiction:toggle_chapter_comment_like', 'fiction:toggle_chapter_comment_like',
        url_kwargs={}, post_url=post_url
    )

    return render(request, 'partials/comment_section.html', {
        'comments': comments,
        'total_count': chapter.comments.filter(status=StatusComment.APPROVED).count(),
        'current_sort': sort,
        'post_url': post_url,
        'refresh_url': reverse('fiction:chapter_comments_partial', kwargs={'pk': pk, 'chapter_number': chapter_number}),
    })