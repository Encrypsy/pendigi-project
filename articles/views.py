from django.db import transaction
from django.http.response import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import F, Avg, Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator

from interactions.notifications import notify_admins
from interactions.views import _attach_comment_meta, _sort_comments
from .models import Articles, Banner, BannerType, Categories, StatusArticle
from .forms import ArticleMetaForm, ArticleUploadForm, BannerForm
from accounts.models import StatusKontributor
from interactions.models import Activity, Comments, Ratings, Bookmarks, StatusComment, ArticleViewHistory
from interactions.forms import CommentForm, RatingForm
from reading_journal.models import ReadingActivity, ActionType
from accounts.decorators import admin_required
from accounts.decorators import admin_required
from .forms import CategoryForm
from fiction.models import Stories, StatusStory as FictionStatusStory


@admin_required
def category_list(request):
    categories = Categories.objects.annotate(article_count=Count('articles'))

    query = request.GET.get('q', '').strip()
    if query:
        categories = categories.filter(name__icontains=query)

    sort = request.GET.get('sort', 'name')
    sort_map = {'name': 'name', 'terbanyak': '-article_count', 'tersedikit': 'article_count'}
    categories = categories.order_by(sort_map.get(sort, 'name'))

    try:
        per_page = int(request.GET.get('per_page', 10))
        if per_page not in (10, 25, 50):
            per_page = 10
    except ValueError:
        per_page = 10

    paginator = Paginator(categories, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    filters = [
        {
            'name': 'sort', 'label': 'Urutan', 'value': sort,
            'options': [('name', 'Nama A-Z'), ('terbanyak', 'Artikel Terbanyak'), ('tersedikit', 'Artikel Tersedikit')],
        },
    ]

    return render(request, 'articles/category_list.html', {
        'page_obj': page_obj,
        'categories': page_obj.object_list,
        'search_query': query,
        'filters': filters,
        'per_page': per_page,
        'per_page_options': [10, 25, 50],
        'reset_url': reverse('articles:category_list'),
    })


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({'ok': True})
            messages.success(request, 'Kategori berhasil ditambahkan.')
            return redirect('articles:category_list')
        if _is_ajax(request):
            return render(request, 'articles/category_form_modal.html', {'form': form, 'is_edit': False}, status=400)
    else:
        form = CategoryForm()

    return render(request, 'articles/category_form_modal.html', {'form': form, 'is_edit': False})


@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Categories, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({'ok': True})
            messages.success(request, 'Kategori berhasil diperbarui.')
            return redirect('articles:category_list')
        if _is_ajax(request):
            return render(request, 'articles/category_form_modal.html', {'form': form, 'is_edit': True, 'category': category}, status=400)
    else:
        form = CategoryForm(instance=category)

    return render(request, 'articles/category_form_modal.html', {'form': form, 'is_edit': True, 'category': category})


@admin_required
@require_POST
def category_bulk_action(request):
    ids = request.POST.getlist('selected_ids')
    action = request.POST.get('bulk_action')

    if not ids:
        messages.error(request, 'Pilih minimal 1 kategori terlebih dahulu.')
        return redirect('articles:category_list')

    qs = Categories.objects.filter(pk__in=ids)

    if action == 'delete':
        blocked = qs.filter(articles__isnull=False).distinct()
        if blocked.exists():
            names = ', '.join(blocked.values_list('name', flat=True))
            messages.error(request, f'Kategori berikut tidak bisa dihapus karena masih dipakai artikel: {names}')
        else:
            count = qs.count()
            qs.delete()
            messages.success(request, f'{count} kategori berhasil dihapus.')
    else:
        messages.error(request, 'Aksi tidak dikenali.')

    return redirect(request.META.get('HTTP_REFERER', reverse('articles:category_list')))


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
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('kategori', '').strip()

    # Artikel yang sudah disetujui
    articles = (
        Articles.objects
        .filter(status=StatusArticle.APPROVED)
        .select_related('category', 'contributor')
    )

    if query:
        articles = articles.filter(title__icontains=query)

    if category_slug:
        articles = articles.filter(
            category__name__iexact=category_slug
        )

    articles = articles.order_by('-created_at')

    categories = Categories.objects.all()

    # Slideshow kategori: maksimal 4 artikel acak
    category_slides = []
    if category_slug and not query:
        category_slides = list(
            articles
            .filter(thumbnail__isnull=False)
            .exclude(thumbnail='')
            .order_by('?')[:4]
        )

    # Pagination berita terkini: 10 artikel per halaman
    paginator = Paginator(articles, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Query khusus artikel dalam kategori aktif
    category_articles = (
        Articles.objects
        .filter(status=StatusArticle.APPROVED)
        .select_related('category', 'contributor')
    )

    if category_slug:
        category_articles = category_articles.filter(
            category__name__iexact=category_slug
        )

    # Sidebar: 4 artikel terpopuler dalam kategori aktif
    category_popular = category_articles.order_by(
        '-views_count', '-created_at'
    )[:4]

    # Rekomendasi editor dari artikel terpopuler
    editor_pick = category_popular.first()

    # Artikel trending untuk beranda
    trending_articles = (
        Articles.objects
        .filter(status=StatusArticle.APPROVED)
        .select_related('category', 'contributor')
        .order_by('-views_count', '-created_at')[:4]
    )

    # Karya fiksi untuk beranda
    featured_stories = (
        Stories.objects
        .filter(status=FictionStatusStory.APPROVED)
        .exclude(cover='')
        .select_related('author')
        .order_by('-views_count')[:12]
    )

    # Artikel terbaru untuk beranda
    latest_articles = (
        Articles.objects
        .filter(status=StatusArticle.APPROVED)
        .select_related('category', 'contributor')
        .order_by('-created_at')[:4]
    )
    
    # ID artikel yang sudah di-bookmark oleh user
    bookmarked_article_ids = []

    if request.user.is_authenticated:
        bookmarked_article_ids = list(
            Bookmarks.objects.filter(
                user=request.user,
                article__isnull=False,
            ).values_list('article_id', flat=True)
        )

    return render(request, 'articles/list.html', {
        'articles': articles,
        'page_obj': page_obj,
        'latest_articles': latest_articles,
        'categories': categories,
        'active_category': category_slug,
        'category_slides': category_slides,
        'category_popular': category_popular,
        'editor_pick': editor_pick,
        'banner_items': Banner.objects.filter(is_active=True),
        'trending_articles': trending_articles,
        'featured_stories': featured_stories,
        'search_query': query,
        'bookmarked_article_ids': bookmarked_article_ids,
    })


def article_detail(request, pk):
    article = get_object_or_404(
        Articles,
        pk=pk,
        status=StatusArticle.APPROVED,
    )

    Articles.objects.filter(pk=pk).update(
        views_count=F('views_count') + 1
    )
    article.refresh_from_db(fields=['views_count'])

    ArticleViewHistory.objects.create(article=article)

    sort = request.GET.get('sort', 'recent')

    comments_qs = article.comments.filter(
        status=StatusComment.APPROVED,
        parent__isnull=True,
    ).select_related('user')

    comments_qs = _sort_comments(comments_qs, sort)

    post_url = reverse(
        'interactions:submit_comment',
        kwargs={'pk': pk},
    )

    comments = _attach_comment_meta(
        comments_qs,
        request,
        'interactions:toggle_comment_like',
        'interactions:toggle_comment_dislike',
        url_kwargs={},
        post_url=post_url,
    )

    # Statistik rating artikel
    rating_stats = article.ratings.aggregate(
        average=Avg('rating_value'),
        total=Count('id'),
    )

    avg_rating = rating_stats['average']
    total_ratings = rating_stats['total']

    user_rating = None
    is_bookmarked = False

    if request.user.is_authenticated:
        is_bookmarked = Bookmarks.objects.filter(
            user=request.user,
            article=article,
        ).exists()

        user_rating_obj = Ratings.objects.filter(
            user=request.user,
            article=article,
        ).values_list(
            'rating_value',
            flat=True,
        ).first()


        if user_rating_obj:
            user_rating = user_rating_obj.rating_value

        ReadingActivity.objects.get_or_create(
            user=request.user,
            article=article,
            action_type=ActionType.STARTED_READING,
        )

    return render(
        request,
        'articles/detail.html',
        {
            'article': article,
            'comments': comments,
            'avg_rating': avg_rating,
            'total_ratings': total_ratings,
            'is_bookmarked': is_bookmarked,
            'user_rating': user_rating,
            'comment_form': CommentForm(),
            'rating_form': RatingForm(),
            'total_count': article.comments.filter(
                status=StatusComment.APPROVED
            ).count(),
            'current_sort': sort,
            'post_url': post_url,
            'refresh_url': reverse(
                'articles:article_comments_partial',
                kwargs={'pk': pk},
            ),
        },
    )


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
    """Upload artikel khusus kontributor terverifikasi."""

    if request.user.status_kontributor != StatusKontributor.APPROVED:
        messages.error(
            request,
            'Anda belum terverifikasi sebagai kontributor.'
        )
        return redirect('articles:article_list')

    if request.method == 'POST':
        form = ArticleUploadForm(request.POST, request.FILES)

        if form.is_valid():
            article = form.save(commit=False)
            article.contributor = request.user
            article.save()
            
            notify_admins(
                actor=request.user,
                message=f"Artikel '{article.title}' menunggu moderasi.",
                action_type=Activity.ActionType.CONTENT_PENDING,
            )

            messages.success(
                request,
                'Artikel berhasil dikirim, menunggu approval admin.'
            )
            return redirect('/accounts/dashboard/penulis/pending/')
    else:
        form = ArticleUploadForm()

    return render(
        request,
        'articles/upload.html',
        {
            'form': form,
            'active_menu': 'create_content',
            'active_create_type': 'article',
            'breadcrumb': 'Buat Konten / Artikel',
        }
    )

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
            
            notify_admins(
                actor=request.user,
                message=f'Artikel "{updated_article.title}" menunggu moderasi ulang.',
                action_type=Activity.ActionType.CONTENT_PENDING,
            )
            
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
def admin_article_approval(request, status='pending'):

    allowed_statuses = {
        'pending': StatusArticle.PENDING,
        'approved': StatusArticle.APPROVED,
        'rejected': StatusArticle.REJECTED,
    }

    if status not in allowed_statuses:
        return redirect('articles:admin_article_approval')

    # =========================
    # DATA ARTIKEL
    # =========================

    articles = Articles.objects.filter(
        status=allowed_statuses[status]
    ).select_related(
        'category',
        'contributor'
    )


    # =========================
    # SEARCH
    # =========================

    query = request.GET.get('q', '').strip()

    if query:
        articles = articles.filter(
            Q(title__icontains=query) |
            Q(contributor__username__icontains=query) |
            Q(category__name__icontains=query)
        )


    # =========================
    # URUTAN
    # =========================

    articles = articles.order_by('-created_at')


    # =========================
    # JUMLAH DATA PER HALAMAN
    # =========================

    try:
        per_page = int(request.GET.get('per_page', 10))

        if per_page not in (10, 25, 50):
            per_page = 10

    except (ValueError, TypeError):
        per_page = 10


    # =========================
    # PAGINATION
    # =========================

    paginator = Paginator(articles, per_page)

    page_number = request.GET.get('page', 1)

    page_obj = paginator.get_page(page_number)


    # =========================
    # JUMLAH ARTIKEL PER STATUS
    # =========================

    status_counts = {
        'pending': Articles.objects.filter(
            status=StatusArticle.PENDING
        ).count(),

        'approved': Articles.objects.filter(
            status=StatusArticle.APPROVED
        ).count(),

        'rejected': Articles.objects.filter(
            status=StatusArticle.REJECTED
        ).count(),
    }


    # =========================
    # RENDER
    # =========================

    return render(
        request,
        'articles/admin_article_approval.html',
        {
            'articles': page_obj.object_list,

            # pagination
            'page_obj': page_obj,
            'per_page': per_page,
            'per_page_options': [10, 25, 50],

            # search
            'search_query': query,

            # status
            'article_status': status,
            'status_counts': status_counts,

            # PENTING:
            # jangan kirim 'filters'
            # karena halaman approval tidak memakai filter.
        }
    )

@admin_required
@require_POST
def admin_approve_article(request, pk):
    article = get_object_or_404(
        Articles,
        pk=pk,
        status=StatusArticle.PENDING,
    )

    with transaction.atomic():
        article.status = StatusArticle.APPROVED
        article.published_at = timezone.now()
        article.rejection_reason = ''
        article.save(update_fields=[
            'status',
            'published_at',
            'rejection_reason',
        ])

        Activity.objects.create(
            recipient=article.contributor,
            actor=request.user,
            article=article,
            action_type=Activity.ActionType.APPROVED,
            message=(
                f'Artikel "{article.title}" telah disetujui oleh admin.'
            )[:255],
        )

    messages.success(
        request,
        f'Artikel "{article.title}" berhasil disetujui.',
    )
    return redirect('articles:admin_article_approval')


@admin_required
@require_POST
def admin_reject_article(request, pk):
    article = get_object_or_404(
        Articles,
        pk=pk,
        status=StatusArticle.PENDING,
    )

    reason = request.POST.get('rejection_reason', '').strip()

    with transaction.atomic():
        article.status = StatusArticle.REJECTED
        article.rejection_reason = reason
        article.save(update_fields=[
            'status',
            'rejection_reason',
        ])

        if reason:
            notification_message = (
                f'Artikel "{article.title}" ditolak oleh admin. '
                f'Alasan: {reason}'
            )
        else:
            notification_message = (
                f'Artikel "{article.title}" ditolak oleh admin.'
            )

        Activity.objects.create(
            recipient=article.contributor,
            actor=request.user,
            article=article,
            action_type=Activity.ActionType.REJECTED,
            message=notification_message[:255],
        )

    messages.warning(
        request,
        f'Artikel "{article.title}" ditolak.',
    )
    return redirect('articles:admin_article_approval')

@admin_required
def admin_review_article(request, pk):
    article = get_object_or_404(Articles, pk=pk)

    return render(
        request,
        'articles/admin_review_article.html',
        {'article': article},
    )

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
    banners = Banner.objects.exclude(type=BannerType.FIKSI)

    query = request.GET.get('q', '').strip()
    if query:
        banners = banners.filter(title__icontains=query)

    status = request.GET.get('status', '')
    if status == 'aktif':
        banners = banners.filter(is_active=True)
    elif status == 'nonaktif':
        banners = banners.filter(is_active=False)

    sort = request.GET.get('sort', 'order')
    sort_map = {
        'order': 'order',
        'terbaru': '-created_at',
        'terlama': 'created_at'
    }
    banners = banners.order_by(sort_map.get(sort, 'order'))

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            banners = banners.filter(created_at__date__gte=parsed)

    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            banners = banners.filter(created_at__date__lte=parsed)

    try:
        per_page = int(request.GET.get('per_page', 10))
        if per_page not in (10, 25, 50):
            per_page = 10
    except ValueError:
        per_page = 10

    paginator = Paginator(banners, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    filters = [
        {
            'name': 'status',
            'label': 'Status',
            'value': status,
            'options': [
                ('', 'Semua Status'),
                ('aktif', 'Aktif'),
                ('nonaktif', 'Nonaktif')
            ],
        },
        {
            'name': 'sort',
            'label': 'Urutan',
            'value': sort,
            'options': [
                ('order', 'Urutan Tampil'),
                ('terbaru', 'Terbaru'),
                ('terlama', 'Terlama')
            ],
        },
    ]

    return render(request, 'articles/banner_list.html', {
        'page_obj': page_obj,
        'banners': page_obj.object_list,
        'search_query': query,
        'filters': filters,
        'date_from': date_from,
        'date_to': date_to,
        'per_page': per_page,
        'per_page_options': [10, 25, 50],
        'reset_url': reverse('articles:banner_list'),
        'banner_page': 'homepage',
    })
    
@admin_required
def fiction_banner_list(request):
    banners = Banner.objects.filter(type=BannerType.FIKSI)

    query = request.GET.get('q', '').strip()
    if query:
        banners = banners.filter(title__icontains=query)

    status = request.GET.get('status', '')
    if status == 'aktif':
        banners = banners.filter(is_active=True)
    elif status == 'nonaktif':
        banners = banners.filter(is_active=False)

    sort = request.GET.get('sort', 'order')

    sort_map = {
        'order': 'order',
        'terbaru': '-created_at',
        'terlama': 'created_at'
    }

    banners = banners.order_by(sort_map.get(sort, 'order'))

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            banners = banners.filter(created_at__date__gte=parsed)

    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            banners = banners.filter(created_at__date__lte=parsed)

    try:
        per_page = int(request.GET.get('per_page', 10))
        if per_page not in (10, 25, 50):
            per_page = 10
    except ValueError:
        per_page = 10

    paginator = Paginator(banners, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    filters = [
        {
            'name': 'status',
            'label': 'Status',
            'value': status,
            'options': [
                ('', 'Semua Status'),
                ('aktif', 'Aktif'),
                ('nonaktif', 'Nonaktif')
            ],
        },
        {
            'name': 'sort',
            'label': 'Urutan',
            'value': sort,
            'options': [
                ('order', 'Urutan Tampil'),
                ('terbaru', 'Terbaru'),
                ('terlama', 'Terlama')
            ],
        },
    ]

    return render(request, 'articles/banner_list.html', {
        'page_obj': page_obj,
        'banners': page_obj.object_list,
        'search_query': query,
        'filters': filters,
        'date_from': date_from,
        'date_to': date_to,
        'per_page': per_page,
        'per_page_options': [10, 25, 50],
        'reset_url': reverse('articles:fiction_banner_list'),
        'banner_page': 'fiction',
    })


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@admin_required
def banner_create(request):
    is_fiction = request.GET.get('page') == 'fiction'

    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES)

        if form.is_valid():
            banner = form.save(commit=False)

            if is_fiction:
                banner.type = BannerType.FIKSI

            banner.save()

            if _is_ajax(request):
                return JsonResponse({'ok': True})

            messages.success(request, 'Banner ditambahkan.')

            if is_fiction:
                return redirect('articles:fiction_banner_list')

            return redirect('articles:banner_list')

    else:
        form = BannerForm()

    return render(request, 'articles/banner_form_modal.html', {
        'form': form,
        'is_edit': False,
        'is_fiction': is_fiction,
    })


@admin_required
def banner_edit(request, pk):
    banner = get_object_or_404(Banner, pk=pk)

    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({'ok': True})
            messages.success(request, 'Banner diperbarui.')
            return redirect('articles:banner_list')
        if _is_ajax(request):
            return render(request, 'articles/banner_form_modal.html', {'form': form, 'is_edit': True, 'banner': banner}, status=400)
    else:
        form = BannerForm(instance=banner)

    return render(request, 'articles/banner_form_modal.html', {'form': form, 'is_edit': True, 'banner': banner})


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
    page = request.GET.get('page', 'homepage')

    if page == 'fiction':
        banners = Banner.objects.filter(
            type=BannerType.FIKSI,
            is_active=True
        )
    else:
        banners = Banner.objects.exclude(
            type=BannerType.FIKSI
        ).filter(
            is_active=True
        )

    return render(
        request,
        'articles/banner_preview.html',
        {
            'banners': banners,
            'banner_page': page,
        }
    )

@admin_required
@require_POST
def banner_bulk_action(request):
    ids = request.POST.getlist('selected_ids')
    action = request.POST.get('bulk_action')

    if not ids:
        messages.error(request, 'Pilih minimal 1 banner terlebih dahulu.')
        return redirect('articles:banner_list')

    qs = Banner.objects.filter(pk__in=ids)

    if action == 'delete':
        count = qs.count()
        qs.delete()
        messages.success(request, f'{count} banner berhasil dihapus.')
    elif action == 'activate':
        qs.update(is_active=True)
        messages.success(request, f'{qs.count()} banner diaktifkan.')
    elif action == 'deactivate':
        qs.update(is_active=False)
        messages.success(request, f'{qs.count()} banner dinonaktifkan.')
    else:
        messages.error(request, 'Aksi tidak dikenali.')

    return redirect(request.META.get('HTTP_REFERER', reverse('articles:banner_list')))

@admin_required
def admin_article_list(request):
    articles = Articles.objects.select_related('category', 'contributor')

    query = request.GET.get('q', '').strip()
    if query:
        articles = articles.filter(title__icontains=query)

    status = request.GET.get('status', '')
    if status:
        articles = articles.filter(status=status)

    category_id = request.GET.get('category', '')
    if category_id:
        articles = articles.filter(category_id=category_id)

    sort = request.GET.get('sort', 'terbaru')
    sort_map = {'terbaru': '-created_at', 'terlama': 'created_at', 'populer': '-views_count'}
    articles = articles.order_by(sort_map.get(sort, '-created_at'))

    try:
        per_page = int(request.GET.get('per_page', 10))
        if per_page not in (10, 25, 50):
            per_page = 10
    except ValueError:
        per_page = 10

    paginator = Paginator(articles, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    filters = [
        {
            'name': 'status', 'label': 'Status', 'value': status,
            'options': [('', 'Semua Status'), ('approved', 'Approved'), ('pending', 'Pending'), ('rejected', 'Rejected')],
        },
        {
            'name': 'category', 'label': 'Kategori', 'value': category_id,
            'options': [('', 'Semua Kategori')] + [(str(c.pk), c.name) for c in Categories.objects.all()],
        },
        {
            'name': 'sort', 'label': 'Urutan', 'value': sort,
            'options': [('terbaru', 'Terbaru'), ('terlama', 'Terlama'), ('populer', 'Terpopuler')],
        },
    ]

    return render(request, 'articles/admin_article_list.html', {
        'page_obj': page_obj,
        'articles': page_obj.object_list,
        'search_query': query,
        'filters': filters,
        'per_page': per_page,
        'per_page_options': [10, 25, 50],
        'reset_url': reverse('articles:admin_article_list'),
        'active_menu': 'master',
    })


@admin_required
def admin_edit_article_meta(request, pk):
    article = get_object_or_404(Articles, pk=pk)

    if request.method == 'POST':
        form = ArticleMetaForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({'ok': True})
            messages.success(request, 'Artikel diperbarui.')
            return redirect('articles:admin_article_list')
        if _is_ajax(request):
            return render(request, 'articles/admin_article_meta_modal.html', {'form': form, 'article': article}, status=400)
    else:
        form = ArticleMetaForm(instance=article)

    return render(request, 'articles/admin_article_meta_modal.html', {'form': form, 'article': article})


@admin_required
@require_POST
def admin_takedown_article(request, pk):
    article = get_object_or_404(Articles, pk=pk)
    article.status = StatusArticle.REJECTED
    article.is_featured = False
    article.save()
    messages.success(request, f'Artikel "{article.title}" dicabut dari tayangan.')
    return redirect(request.META.get('HTTP_REFERER', reverse('articles:admin_article_list')))


@admin_required
@require_POST
def admin_toggle_featured(request, pk):
    article = get_object_or_404(Articles, pk=pk, status=StatusArticle.APPROVED)
    article.is_featured = not article.is_featured
    article.save()
    return redirect(request.META.get('HTTP_REFERER', reverse('articles:admin_article_list')))


@admin_required
@require_POST
def admin_article_bulk_action(request):
    ids = request.POST.getlist('selected_ids')
    action = request.POST.get('bulk_action')

    if not ids:
        messages.error(request, 'Pilih minimal 1 artikel terlebih dahulu.')
        return redirect('articles:admin_article_list')

    qs = Articles.objects.filter(pk__in=ids)

    if action == 'delete':
        count = qs.count()
        qs.delete()
        messages.success(request, f'{count} artikel dihapus permanen.')
    elif action == 'takedown':
        qs.update(status=StatusArticle.REJECTED, is_featured=False)
        messages.success(request, f'{qs.count()} artikel dicabut dari tayangan.')
    elif action == 'feature':
        count = qs.filter(status=StatusArticle.APPROVED).update(is_featured=True)
        messages.success(request, f'{count} artikel dijadikan unggulan.')
    else:
        messages.error(request, 'Aksi tidak dikenali.')

    return redirect(request.META.get('HTTP_REFERER', reverse('articles:admin_article_list')))