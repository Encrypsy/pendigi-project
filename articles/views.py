from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Avg
from .models import Articles, Categories, StatusArticle
from .forms import ArticleUploadForm
from accounts.models import StatusKontributor
from interactions.models import Comments, Ratings, Bookmarks, StatusComment
from interactions.forms import CommentForm, RatingForm
from reading_journal.models import ReadingActivity, ActionType


def article_list(request):
    """Use case: Baca & tandai artikel selesai (halaman index)"""
    articles = Articles.objects.filter(status=StatusArticle.APPROVED).select_related('category', 'contributor')

    category_slug = request.GET.get('kategori')
    if category_slug:
        articles = articles.filter(category__name__iexact=category_slug)

    categories = Categories.objects.all()

    return render(request, 'articles/list.html', {
        'articles': articles,
        'categories': categories,
        'active_category': category_slug,
    })


def article_detail(request, pk):
    article = get_object_or_404(Articles, pk=pk, status=StatusArticle.APPROVED)

    comments = article.comments.filter(
        status=StatusComment.APPROVED, parent__isnull=True
    ).select_related('user').prefetch_related('replies__user')

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