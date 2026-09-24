from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import F, Avg, Count

from interactions.views import _attach_comment_meta, _sort_comments
from .models import Articles, Banner, Categories, StatusArticle
from .forms import ArticleUploadForm, BannerForm
from accounts.models import StatusKontributor
from interactions.models import Comments, Ratings, Bookmarks, StatusComment
from interactions.forms import CommentForm, RatingForm
from reading_journal.models import ReadingActivity, ActionType
from django.utils import timezone
from accounts.decorators import admin_required
from accounts.decorators import admin_required
from .forms import CategoryForm
from fiction.models import Stories, StatusStory as FictionStatusStory


@admin_required
def category_list(request):
    categories = Categories.objects.annotate(article_count=Count('articles')).order_by('name')
    return render(request, 'articles/category_list.html', {'categories': categories})


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kategori berhasil ditambahkan.')
            return redirect('articles:category_list')
    else:
        form = CategoryForm()

    return render(request, 'articles/category_form.html', {'form': form, 'is_edit': False})


@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Categories, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kategori berhasil diperbarui.')
            return redirect('articles:category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'articles/category_form.html', {'form': form, 'is_edit': True, 'category': category})


@admin_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Categories, pk=pk)

    if category.articles.exists():
        messages.error(request, f'Kategori "{category.name}" tidak bisa dihapus karena masih dipakai {category.articles.count()} artikel.')
        return redirect('articles:category_list')

    category.delete()
    messages.success(request, 'Kategori berhasil dihapus.')
    return redirect('articles:category_list')


def article_list(request):
    articles = Articles.objects.filter(
        status=StatusArticle.APPROVED
        ).select_related(
            'category', 
            'contributor'
        ).order_by('-created_at')[:4]

    query = request.GET.get('q', '').strip()
    if query:
        articles = articles.filter(title__icontains=query)

    category_slug = request.GET.get('kategori')
    if category_slug:
        articles = articles.filter(category__name__iexact=category_slug)

    categories = Categories.objects.all()

    banner_items = Banner.objects.filter(is_active=True)

    trending_articles = Articles.objects.filter(
        status=StatusArticle.APPROVED
    ).select_related('category').order_by('-views_count')[:4]

    featured_stories = Stories.objects.filter(
        status=FictionStatusStory.APPROVED
    ).exclude(cover='').select_related('author').order_by('-views_count')[:12]

    return render(request, 'articles/list.html', {
        'articles': articles,
        'categories': categories,
        'active_category': category_slug,
        'banner_items': banner_items,
        'trending_articles': trending_articles,
        'featured_stories': featured_stories,
        'search_query': query,
    })


def article_detail(request, pk):
    article = get_object_or_404(Articles, pk=pk, status=StatusArticle.APPROVED)

    Articles.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    article.refresh_from_db(fields=['views_count'])

    sort = request.GET.get('sort', 'recent')
    comments_qs = article.comments.filter(status=StatusComment.APPROVED, parent__isnull=True).select_related('user')
    comments_qs = _sort_comments(comments_qs, sort)
    post_url = reverse('interactions:submit_comment', kwargs={'pk': pk})
    comments = _attach_comment_meta(
        comments_qs, request,
        'interactions:toggle_comment_like', 'interactions:toggle_comment_dislike',
        url_kwargs={}, post_url=post_url
    )

    avg_rating = article.ratings.aggregate(avg=Avg('rating_value'))['avg']

    is_bookmarked = False
    user_rating = None
    if request.user.is_authenticated:
        is_bookmarked = Bookmarks.objects.filter(user=request.user, article=article).exists()
        user_rating_obj = Ratings.objects.filter(user=request.user, article=article).first()
        user_rating = user_rating_obj.rating_value if user_rating_obj else None

        ReadingActivity.objects.get_or_create(
            user=request.user, article=article, action_type=ActionType.STARTED_READING
        )

    return render(request, 'articles/detail.html', {
        'article': article,
        'comments': comments,
        'avg_rating': avg_rating,
        'is_bookmarked': is_bookmarked,
        'user_rating': user_rating,
        'comment_form': CommentForm(),
        'rating_form': RatingForm(),
        'total_count': article.comments.filter(status=StatusComment.APPROVED).count(),
        'current_sort': sort,
        'post_url': reverse('interactions:submit_comment', kwargs={'pk': pk}),
        'refresh_url': reverse('articles:article_comments_partial', kwargs={'pk': pk}),
    })


@login_required
def mark_as_finished(request, pk):
    """Use case: Baca & tandai artikel selesai -> <<include>> Isi catatan pribadi/insight"""
    article = get_object_or_404(Articles, pk=pk, status=StatusArticle.APPROVED)

    ReadingActivity.objects.get_or_create(
        user=request.user, article=article, action_type=ActionType.FINISHED_READING
    )
    messages.success(request, 'Artikel ditandai selesai dibaca. Mau catat insight-nya?')
    return redirect('reading_journal:add_note', article_id=article.pk)


@login_required
def upload_article(request):
    """Use case: Upload artikel (khusus Kontributor)"""
    if request.user.status_kontributor != StatusKontributor.APPROVED:
        messages.error(request, 'Anda belum terverifikasi sebagai kontributor.')
        return redirect('articles:article_list')

    if request.method == 'POST':
        form = ArticleUploadForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.contributor = request.user
            article.save()
            messages.success(request, 'Artikel berhasil dikirim, menunggu approval admin.')
            return redirect('articles:my_articles')
    else:
        form = ArticleUploadForm()

    return render(request, 'articles/upload.html', {'form': form})


@login_required
def my_articles(request):
    """Kontributor memantau status artikel yang sudah diupload"""
    if request.user.status_kontributor != StatusKontributor.APPROVED:
        messages.error(request, 'Anda belum terverifikasi sebagai kontributor.')
        return redirect('articles:article_list')

    articles = request.user.articles.all()
    return render(request, 'articles/my_articles.html', {'articles': articles})

@login_required
def edit_article(request, pk):
    article = get_object_or_404(Articles, pk=pk, contributor=request.user)

    if request.method == 'POST':
        form = ArticleUploadForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            updated_article = form.save(commit=False)
            updated_article.status = StatusArticle.PENDING
            updated_article.published_at = None
            updated_article.save()
            messages.success(request, 'Artikel diperbarui, menunggu approval ulang dari admin.')
            return redirect('articles:my_articles')
    else:
        form = ArticleUploadForm(instance=article)

    return render(request, 'articles/upload.html', {
        'form': form,
        'is_edit': True,
        'article': article,
    })


@login_required
@require_POST
def delete_article(request, pk):
    article = get_object_or_404(Articles, pk=pk, contributor=request.user)
    article.delete()
    messages.success(request, 'Artikel berhasil dihapus.')
    return redirect('articles:my_articles')

@admin_required
def admin_pending_articles(request):
    articles = Articles.objects.filter(status=StatusArticle.PENDING).select_related('category', 'contributor')
    return render(request, 'articles/admin_pending.html', {'articles': articles})


@admin_required
@require_POST
def admin_approve_article(request, pk):
    article = get_object_or_404(Articles, pk=pk)
    article.status = StatusArticle.APPROVED
    article.published_at = timezone.now()
    article.save()
    messages.success(request, f'Artikel "{article.title}" disetujui.')
    return redirect('articles:admin_pending_articles')


@admin_required
@require_POST
def admin_reject_article(request, pk):
    article = get_object_or_404(Articles, pk=pk)
    article.status = StatusArticle.REJECTED
    article.save()
    messages.success(request, f'Artikel "{article.title}" ditolak.')
    return redirect('articles:admin_pending_articles')

def article_comments_partial(request, pk):
    article = get_object_or_404(Articles, pk=pk, status=StatusArticle.APPROVED)
    sort = request.GET.get('sort', 'recent')
    comments_qs = article.comments.filter(status=StatusComment.APPROVED, parent__isnull=True).select_related('user')
    comments_qs = _sort_comments(comments_qs, sort)
    post_url = reverse('interactions:submit_comment', kwargs={'pk': pk})
    comments = _attach_comment_meta(
        comments_qs, request,
        'interactions:toggle_comment_like', 'interactions:toggle_comment_dislike',
        url_kwargs={}, post_url=post_url
    )

    return render(request, 'partials/comment_section.html', {
        'comments': comments,
        'total_count': article.comments.filter(status=StatusComment.APPROVED).count(),
        'current_sort': sort,
        'post_url': reverse('interactions:submit_comment', kwargs={'pk': pk}),
        'refresh_url': reverse('articles:article_comments_partial', kwargs={'pk': pk}),
    })

@admin_required
def banner_list(request):
    banners = Banner.objects.all()
    return render(request, 'articles/banner_list.html', {'banners': banners})


@admin_required
def banner_create(request):
    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banner berhasil ditambahkan.')
            return redirect('articles:banner_list')
    else:
        form = BannerForm()
    return render(request, 'articles/banner_form.html', {'form': form})


@admin_required
@require_POST
def banner_delete(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.delete()
    messages.success(request, 'Banner dihapus.')
    return redirect('articles:banner_list')


@admin_required
@require_POST
def banner_toggle_active(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.is_active = not banner.is_active
    banner.save()
    return redirect('articles:banner_list')


def banner_preview(request):
    banners = Banner.objects.filter(is_active=True)
    return render(request, 'articles/banner_preview.html', {'banners': banners})