from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.shortcuts import get_object_or_404, render, redirect

from accounts.services import approve_contributor_application, reject_contributor_application
from .forms import AdminUserEditForm, RegisterForm, ContributorApplicationForm, ProfileUpdateForm
from .models import StatusKontributor, ContributorApplication, Users
from .decorators import admin_required
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from articles.models import Articles, StatusArticle, Categories
from interactions.models import Activity, ArticleViewHistory, Comments, StatusComment, Ratings
from articles.models import Articles, StatusArticle, Categories
from fiction.models import Chapters, StatusChapter, Stories, StatusStory as FictionStatusStory
from reading_journal.models import ReadingActivity
from datetime import timedelta
from django.views.decorators.http import require_POST
from .models import Follow
import json
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from interactions.notifications import notify_admins


@login_required
@require_POST
def toggle_follow(request, username):
    target_user = get_object_or_404(
        Users,
        username=username,
    )

    # Mencegah pengguna mengikuti dirinya sendiri
    if target_user == request.user:
        messages.error(
            request,
            'Tidak bisa follow diri sendiri.',
        )
        return redirect(
            request.META.get(
                'HTTP_REFERER',
                'articles:article_list',
            )
        )

    # Membuat atau menghapus hubungan follow
    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=target_user,
    )

    if not created:
        # Unfollow tidak membuat notifikasi baru
        follow.delete()

        messages.info(
            request,
            f'Berhenti mengikuti {target_user.username}.',
        )

    else:
        # Buat notifikasi untuk pengguna yang diikuti
        from interactions.models import Activity

        Activity.objects.create(
            recipient=target_user,
            actor=request.user,
            action_type=Activity.ActionType.FOLLOW,
            message=f'{request.user.username} mulai mengikuti kamu.',
        )

        messages.success(
            request,
            f'Mengikuti {target_user.username}.',
        )

    return redirect(
        request.META.get(
            'HTTP_REFERER',
            'articles:article_list',
        )
    )



class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Akun berhasil dibuat!')
            return redirect('articles:article_list')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def apply_contributor(request):
    if request.method == 'POST':
        with transaction.atomic():
            user = Users.objects.select_for_update().get(
                pk=request.user.pk
            )

            # Pengguna yang sudah disetujui tidak bisa mendaftar lagi.
            if user.status_kontributor == StatusKontributor.APPROVED:
                messages.info(
                    request,
                    'Anda sudah menjadi kontributor.',
                )
                return redirect('articles:article_list')

            # Cegah pengajuan pending ganda.
            has_pending_application = (
                ContributorApplication.objects.filter(
                    user=user,
                    status=StatusKontributor.PENDING,
                ).exists()
            )

            if has_pending_application:
                messages.info(
                    request,
                    'Pengajuan kamu masih menunggu verifikasi admin.',
                )
                return redirect(
                    'contributor_application_status'
                )

            form = ContributorApplicationForm(request.POST)

            if form.is_valid():
                application = form.save(commit=False)
                application.user = user
                application.email = user.email
                application.status = StatusKontributor.PENDING
                application.save()

                user.status_kontributor = StatusKontributor.PENDING
                user.save(update_fields=['status_kontributor'])

                notify_admins(
                    actor=user,
                    message=(
                        f'{application.full_name} mengajukan diri '
                        'sebagai kontributor.'
                    ),
                    action_type=Activity.ActionType.CONTRIBUTOR_APPLICATION,
                )

                messages.success(
                    request,
                    'Pengajuan berhasil dikirim! '
                    'Silakan tunggu verifikasi admin.',
                )

                return redirect(
                    'contributor_application_status'
                )

    else:
        user = request.user

        if user.status_kontributor == StatusKontributor.APPROVED:
            messages.info(
                request,
                'Anda sudah menjadi kontributor.',
            )
            return redirect('articles:article_list')

        has_pending_application = (
            ContributorApplication.objects.filter(
                user=user,
                status=StatusKontributor.PENDING,
            ).exists()
        )

        if has_pending_application:
            messages.info(
                request,
                'Pengajuan kamu masih menunggu verifikasi admin.',
            )
            return redirect(
                'contributor_application_status'
            )

        form = ContributorApplicationForm()

    return render(
        request,
        'accounts/apply_contributor.html',
        {'form': form},
    )

@login_required
def profile_view(request, username=None):
    # Profil sendiri atau profil publik
    if username:
        profile_user = get_object_or_404(
            Users,
            username=username,
        )
    else:
        profile_user = request.user

    is_own_profile = profile_user.pk == request.user.pk

    # Statistik follow
    followers_count = Follow.objects.filter(
        following=profile_user,
    ).count()

    following_count = Follow.objects.filter(
        follower=profile_user,
    ).count()

    is_following = False

    if not is_own_profile:
        is_following = Follow.objects.filter(
            follower=request.user,
            following=profile_user,
        ).exists()

    # Artikel yang sudah disetujui
    published_articles = list(
        profile_user.articles.filter(
            status='approved',
        ).select_related(
            'category',
        ).order_by('-pk')
    )

    # Cerita fiksi yang sudah disetujui
    published_stories = list(
        profile_user.stories.filter(
            status='approved',
        ).order_by('-pk')
    )

    # Tambahkan tipe karya agar template dapat membedakan
    for article in published_articles:
        article.work_type = 'article'
        article.work_date = getattr(article, 'created_at', None)

    for story in published_stories:
        story.work_type = 'story'
        story.work_date = getattr(story, 'created_at', None)

    # Gabungkan karya, urutkan dari yang terbaru
    all_works = published_articles + published_stories

    all_works.sort(
        key=lambda work: (
            work.work_date is not None,
            work.work_date if work.work_date is not None else work.pk,
            work.pk,
        ),
        reverse=True,
    )

    showcase_works = all_works[:3]
    published_count = len(all_works)

    # Data yang hanya diperlukan di profil sendiri
    favorites = []
    stories = []
    form = None

    if is_own_profile:
        favorites = request.user.favorite_articles.select_related(
            'article',
        ).all()

        if request.method == 'POST':
            form = ProfileUpdateForm(
                request.POST,
                request.FILES,
                instance=request.user,
            )

            if form.is_valid():
                form.save()
                messages.success(
                    request,
                    'Profil berhasil diperbarui!',
                )
                return redirect('profile')
        else:
            form = ProfileUpdateForm(
                instance=request.user,
            )

    return render(
        request,
        'accounts/profile.html',
        {
            'profile_user': profile_user,
            'is_own_profile': is_own_profile,
            'is_following': is_following,
            'followers_count': followers_count,
            'following_count': following_count,
            'showcase_works': showcase_works,
            'published_count': published_count,
            'favorites': favorites,
            'form': form,
        },
    )

    

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user,
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Profil berhasil diperbarui!',
            )
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(
        request,
        'accounts/edit_profile.html',
        {'form': form},
    )

@admin_required
def dashboard_view(request):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    stats = {
        'total_users': Users.objects.filter(role='pembaca').count(),
        'new_users_week': Users.objects.filter(date_joined__gte=seven_days_ago).count(),
        'total_kontributor': Users.objects.filter(status_kontributor=StatusKontributor.APPROVED).count(),
        'total_articles': Articles.objects.count(),
        'new_articles_week': Articles.objects.filter(created_at__gte=seven_days_ago).count(),
        'total_stories': Stories.objects.count(),
        'pending_articles': Articles.objects.filter(status=StatusArticle.PENDING).count(),
        'pending_comments': Comments.objects.filter(status=StatusComment.PENDING).count(),
        'pending_contributors': ContributorApplication.objects.filter(status=StatusKontributor.PENDING).count(),
        'pending_stories': Stories.objects.filter(status=FictionStatusStory.PENDING).count(),
        'total_categories': Categories.objects.count(),
    }

    # --- Data grafik: user baru & interaksi per hari (30 hari terakhir) ---
    users_per_day = (
        Users.objects.filter(date_joined__gte=thirty_days_ago)
        .annotate(day=TruncDate('date_joined'))
        .values('day').annotate(count=Count('id')).order_by('day')
    )
    activity_per_day = (
        ReadingActivity.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day').annotate(count=Count('id')).order_by('day')
    )

    date_labels = [(thirty_days_ago + timedelta(days=i)).date() for i in range(31)]
    users_map = {row['day']: row['count'] for row in users_per_day}
    activity_map = {row['day']: row['count'] for row in activity_per_day}

    chart_labels = [d.strftime('%d %b') for d in date_labels]
    chart_new_users = [users_map.get(d, 0) for d in date_labels]
    chart_interactions = [activity_map.get(d, 0) for d in date_labels]

    # --- Distribusi status konten (artikel + fiksi digabung) ---
    status_counts = {'approved': 0, 'pending': 0, 'rejected': 0}
    for status, count in Articles.objects.values_list('status').annotate(c=Count('id')).values_list('status', 'c'):
        status_counts[status] = status_counts.get(status, 0) + count
    for status, count in Stories.objects.values_list('status').annotate(c=Count('id')).values_list('status', 'c'):
        status_counts[status] = status_counts.get(status, 0) + count

    # --- Artikel per kategori ---
    articles_per_category = Categories.objects.annotate(article_count=Count('articles')).order_by('-article_count')

    popular_articles = Articles.objects.filter(status=StatusArticle.APPROVED).order_by('-views_count')[:5]

    return render(request, 'accounts/dashboard.html', {
        'stats': stats,
        'popular_articles': popular_articles,
        'articles_per_category': articles_per_category,
        'chart_labels': json.dumps(chart_labels),
        'chart_new_users': json.dumps(chart_new_users),
        'chart_interactions': json.dumps(chart_interactions),
        'status_labels': json.dumps(['Approved', 'Pending', 'Rejected']),
        'status_data': json.dumps([status_counts['approved'], status_counts['pending'], status_counts['rejected']]),
        'category_labels': json.dumps([c.name for c in articles_per_category]),
        'category_data': json.dumps([c.article_count for c in articles_per_category]),
    })
    
@login_required
def author_dashboard(request):

    if request.user.status_kontributor != 'approved':
        return redirect('articles:article_list')

    # ==========================================
    # SEMUA KONTEN MILIK PENULIS
    # ==========================================

    my_articles = Articles.objects.filter(
        contributor=request.user
    ).select_related('category')
    
    popular_contents = (
    my_articles
    .filter(status=StatusArticle.APPROVED)
    .annotate(
        total_comments=Count(
            'comments',
            filter=models.Q(
                comments__status=StatusComment.APPROVED
            )
        )
    )
    .order_by(
        '-views_count',
        '-total_comments'
    )[:3]
)


    # ==========================================
    # STAT CARD
    # ==========================================

    approved_count = my_articles.filter(
        status=StatusArticle.APPROVED
    ).count()

    pending_count = my_articles.filter(
        status=StatusArticle.PENDING
    ).count()

    rejected_count = my_articles.filter(
        status=StatusArticle.REJECTED
    ).count()


    # ==========================================
    # HISTORY VIEW
    # ==========================================

    view_history = ArticleViewHistory.objects.filter(
        article__contributor=request.user
    )
    
    # ==========================================
    # FILTER PERFORMA
    # ==========================================

    performance_filter = request.GET.get('period', '30')

    today = timezone.localdate()

    if performance_filter == '7':
        start_date = today - timedelta(days=6)

    elif performance_filter == '30':
        start_date = today - timedelta(days=29)

    elif performance_filter == 'month':
        start_date = today.replace(day=1)

    else:
        performance_filter = '30'
        start_date = today - timedelta(days=29)


    # ==========================================
    # BASELINE VIEW SEBELUM PERIODE
    # ==========================================

    baseline_views = view_history.filter(
        viewed_at__date__lt=start_date
    ).count()


    # ==========================================
    # VIEW DI DALAM PERIODE
    # ==========================================

    filtered_view_history = view_history.filter(
        viewed_at__date__gte=start_date,
        viewed_at__date__lte=today
    )

    # ==========================================
    # VIEW PER TANGGAL
    # ==========================================

    daily_views = (
        filtered_view_history
        .annotate(date=TruncDate('viewed_at'))
        .values('date')
        .annotate(total=Count('id'))
        .order_by('date')
    )


    # ==========================================
    # DATA GRAFIK PERFORMA
    # CUMULATIVE VIEWS
    # ==========================================

    performance_data = []

    cumulative = baseline_views

    for item in daily_views:

        cumulative += item['total']

        performance_data.append({
            'date': item['date'].strftime('%b %-d'),
            'views': cumulative,
        })


    # ==========================================
    # BAR CHART
    # PERFORMA KONTEN BERDASARKAN VIEWS
    # ==========================================

    performance_articles = my_articles.order_by(
        '-views_count'
    )[:10]

    performance_labels = [
        article.title
        for article in performance_articles
    ]

    performance_views = [
        article.views_count
        for article in performance_articles
    ]


    # ==========================================
    # DONUT CHART
    # DISTRIBUSI STATUS
    # ==========================================

    distribution_labels = [
        'Approved',
        'Pending',
        'Rejected',
    ]

    distribution_values = [
        approved_count,
        pending_count,
        rejected_count,
    ]
    
    # ==========================================
    # NOTIFIKASI AKTIVITAS
    # ==========================================

    activities = (
        Activity.objects
        .filter(recipient=request.user)
        .select_related(
            'actor',
            'article',
            'chapter',
            'chapter__story',
        )
        .order_by('-created_at')[:2]
    )

    total_activities = Activity.objects.filter(
        recipient=request.user
    ).count()

    # ==========================================
    # RENDER
    # ==========================================

    return render(
    request,
    'author_dashboard.html',
    {
        'breadcrumb': 'Dashboard Penulis',
        'active_menu': 'dashboard',

        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,

        'performance_data': json.dumps(
            performance_data
        ),

        'performance_labels': json.dumps(
            performance_labels
        ),

        'performance_views': json.dumps(
            performance_views
        ),

        'distribution_labels': json.dumps(
            distribution_labels
        ),

        'distribution_values': json.dumps(
            distribution_values
        ),

        'performance_filter': performance_filter,
        'popular_contents': popular_contents,
        'activities': activities,
        'total_activities': total_activities,
    }
)

@admin_required
def admin_pending_contributors(request):
    applications = ContributorApplication.objects.filter(
        status=StatusKontributor.PENDING
    ).select_related('user')
    return render(request, 'accounts/admin_pending_contributors.html', {'applications': applications})


@admin_required
@require_POST
def admin_approve_contributor(request, pk):
    application = get_object_or_404(
        ContributorApplication,
        pk=pk,
    )

    approve_contributor_application(
        application_id=application.pk,
        actor=request.user,
    )

    messages.success(
        request,
        f'{application.user.username} disetujui sebagai kontributor.',
    )

    return redirect('admin_pending_contributors')


@admin_required
@require_POST
def admin_reject_contributor(request, pk):
    application = get_object_or_404(
        ContributorApplication,
        pk=pk,
        status=StatusKontributor.PENDING,
    )

    admin_notes = request.POST.get('admin_notes', '').strip()

    if not admin_notes:
        messages.error(
            request,
            'Alasan penolakan wajib diisi.',
        )
        return redirect('admin_pending_contributors')

    reject_contributor_application(
        application_id=application.pk,
        actor=request.user,
        admin_notes=admin_notes,
    )

    messages.success(
        request,
        f'Pengajuan {application.user.username} berhasil ditolak.',
    )

    return redirect('admin_pending_contributors')


@login_required
def author_my_content(request):
    if request.user.status_kontributor != StatusKontributor.APPROVED:
        return redirect('articles:article_list')

    # Jenis konten yang dipilih
    content_type = request.GET.get('jenis', 'semua')

    # Pencarian judul
    search_query = request.GET.get('q', '').strip()

    # Pengurutan
    sort_by = request.GET.get('sort', 'terbaru')
    valid_sorts = ['terbaru', 'terlama', 'views', 'rating']

    if sort_by not in valid_sorts:
        sort_by = 'terbaru'

    contents = []

    # Artikel yang sudah disetujui admin
    if content_type in ['semua', 'artikel']:
        articles = (
            Articles.objects
            .filter(
                contributor=request.user,
                status=StatusArticle.APPROVED,
            )
            .select_related('category')
            .annotate(average_rating=Avg('ratings__rating_value'))
        )

        if search_query:
            articles = articles.filter(title__icontains=search_query)

        for article in articles:
            contents.append({
                'id': article.pk,
                'title': article.title,
                'thumbnail': article.thumbnail,
                'views': article.views_count,
                'rating': article.average_rating,
                'created_at': article.published_at or article.created_at,
                'type': 'artikel',
                'edit_url': None,
                'delete_url': None,
            })

    # Fiksi: hanya bab yang sudah disetujui
    if content_type in ['semua', 'fiksi']:
        stories = (
            Stories.objects
            .filter(author=request.user)
            .prefetch_related('chapters')
        )

        if search_query:
            stories = stories.filter(title__icontains=search_query)

        for story in stories:
            approved_chapters = story.chapters.filter(
                status=StatusChapter.APPROVED
            )

            if approved_chapters.exists():
                contents.append({
                    'id': story.pk,
                    'title': story.title,
                    'thumbnail': story.cover,
                    'views': story.views_count,
                    'rating': None,
                    'created_at': story.created_at,
                    'type': 'fiksi',
                    'chapters': approved_chapters,
                })

        # Urutkan gabungan artikel dan fiksi
        if sort_by == 'terbaru':
            contents.sort(key=lambda item: item['created_at'], reverse=True)
        elif sort_by == 'terlama':
            contents.sort(key=lambda item: item['created_at'])
        elif sort_by == 'views':
            contents.sort(key=lambda item: item['views'], reverse=True)
        elif sort_by == 'rating':
            contents.sort(
                key=lambda item: (
                    item['rating'] is not None,
                    item['rating'] or 0,
                ),
                reverse=True,
            )

    # Pagination: 10 konten per halaman
    paginator = Paginator(contents, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/author_my_content.html', {
        'page_obj': page_obj,
        'content_type': content_type,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_contents': len(contents),
        'breadcrumb': 'Konten Saya',
        'active_menu': 'my_content',
    })
    
@login_required
def author_pending_content(request):
    if request.user.status_kontributor != StatusKontributor.APPROVED:
        return redirect('articles:article_list')

    content_type = request.GET.get('jenis', 'semua')
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'terbaru')

    if content_type not in ['semua', 'artikel', 'fiksi']:
        content_type = 'semua'

    if sort_by not in ['terbaru', 'terlama', 'views']:
        sort_by = 'terbaru'

    contents = []

    if content_type in ['semua', 'artikel']:
        articles = Articles.objects.filter(
            contributor=request.user,
            status=StatusArticle.PENDING
        )

        if search_query:
            articles = articles.filter(title__icontains=search_query)

        for article in articles:
            contents.append({
                'id': article.pk,
                'title': article.title,
                'thumbnail': article.thumbnail,
                'views': article.views_count,
                'created_at': article.created_at,
                'type': 'artikel',
                'status': 'Menunggu Approval',
            })

    # Fiksi: hanya bab yang masih menunggu approval
    if content_type in ['semua', 'fiksi']:
        stories = Stories.objects.filter(
            author=request.user
        )

        if search_query:
            stories = stories.filter(title__icontains=search_query)

        for story in stories:
            pending_chapters = story.chapters.filter(
                status=StatusChapter.PENDING
            )

            if pending_chapters.exists():
                contents.append({
                    'id': story.pk,
                    'title': story.title,
                    'thumbnail': story.cover,
                    'views': story.views_count,
                    'created_at': story.created_at,
                    'type': 'fiksi',
                    'status': 'Menunggu Approval',
                    'chapters': pending_chapters,
                })

    if sort_by == 'terbaru':
        contents.sort(key=lambda item: item['created_at'], reverse=True)
    elif sort_by == 'terlama':
        contents.sort(key=lambda item: item['created_at'])
    elif sort_by == 'views':
        contents.sort(key=lambda item: item['views'], reverse=True)

    paginator = Paginator(contents, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/author_pending_content.html', {
        'page_obj': page_obj,
        'content_type': content_type,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_contents': len(contents),
        'breadcrumb': 'Pending',
        'active_menu': 'pending',
    })
    
@login_required
def author_rejected_content(request):
    if request.user.status_kontributor != StatusKontributor.APPROVED:
        return redirect('articles:article_list')

    content_type = request.GET.get('jenis', 'semua')
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'terbaru')

    if content_type not in ['semua', 'artikel', 'fiksi']:
        content_type = 'semua'

    if sort_by not in ['terbaru', 'terlama', 'views']:
        sort_by = 'terbaru'

    contents = []

    # Artikel yang ditolak
    if content_type in ['semua', 'artikel']:
        articles = Articles.objects.filter(
            contributor=request.user,
            status=StatusArticle.REJECTED,
        )

        if search_query:
            articles = articles.filter(title__icontains=search_query)

        for article in articles:
            contents.append({
                'id': article.pk,
                'title': article.title,
                'thumbnail': article.thumbnail,
                'views': article.views_count,
                'created_at': article.created_at,
                'type': 'artikel',
                'rejection_reason': getattr(
                    article, 'rejection_reason', ''
                ),
            })

    # Bab fiksi yang ditolak
    if content_type in ['semua', 'fiksi']:
        chapters = Chapters.objects.filter(
            story__author=request.user,
            status=StatusChapter.REJECTED,
        ).select_related('story')

        if search_query:
            chapters = chapters.filter(
                models.Q(story__title__icontains=search_query)
                | models.Q(title__icontains=search_query)
            )

        for chapter in chapters:
            contents.append({
                'id': chapter.pk,
                'story_id': chapter.story_id,
                'title': chapter.story.title,
                'chapter_title': chapter.title,
                'chapter_number': chapter.chapter_number,
                'thumbnail': chapter.story.cover,
                'views': chapter.views_count,
                'created_at': chapter.created_at,
                'type': 'fiksi',
                'rejection_reason': chapter.rejection_reason,
            })

    if sort_by == 'terbaru':
        contents.sort(key=lambda item: item['created_at'], reverse=True)
    elif sort_by == 'terlama':
        contents.sort(key=lambda item: item['created_at'])
    elif sort_by == 'views':
        contents.sort(key=lambda item: item['views'], reverse=True)

    paginator = Paginator(contents, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/author_rejected_content.html', {
        'page_obj': page_obj,
        'content_type': content_type,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_contents': len(contents),
        'breadcrumb': 'Konten Ditolak',
        'active_menu': 'rejected',
    })
    
@login_required
def author_notifications(request):
    if request.user.status_kontributor != StatusKontributor.APPROVED:
        return redirect('articles:article_list')

    activities = (
        Activity.objects
        .filter(recipient=request.user)
        .select_related(
            'actor',
            'article',
            'chapter',
            'chapter__story',
        )
        .order_by('-created_at')
    )

    paginator = Paginator(activities, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'accounts/author_notifications.html',
        {
            'page_obj': page_obj,
            'breadcrumb': 'Notifikasi',
            'active_menu': 'notifications',
        },
    )
    
def admin_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_staff
    )(view_func)


@admin_required
def admin_user_list(request):
    users = Users.objects.all().order_by('-date_joined')

    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    status = request.GET.get('status', '').strip()

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    if role == 'kontributor':
        users = users.filter(
            status_kontributor=StatusKontributor.APPROVED
        )
    elif role == 'pembaca':
        users = users.filter(role='pembaca')

    if status == 'aktif':
        users = users.filter(is_active=True)
    elif status == 'nonaktif':
        users = users.filter(is_active=False)

    return render(request, 'accounts/admin_user_list.html', {
        'users': users,
        'query': query,
        'selected_role': role,
        'selected_status': status,
        'total_users': Users.objects.count(),
    })


@admin_required
def admin_user_detail(request, pk):
    user_obj = get_object_or_404(Users, pk=pk)

    return render(request, 'accounts/admin_user_detail.html', {
        'user_obj': user_obj,
    })
    
@admin_required
def admin_user_edit(request, pk):
    user_obj = get_object_or_404(Users, pk=pk)

    # Lindungi akun superuser dari perubahan melalui halaman ini.
    if user_obj.is_superuser:
        messages.error(
            request,
            'Akun superuser tidak dapat diedit melalui halaman ini.'
        )
        return redirect('admin_user_detail', pk=user_obj.pk)

    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=user_obj)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Akun {user_obj.username} berhasil diperbarui.'
            )
            return redirect('admin_user_detail', pk=user_obj.pk)
    else:
        form = AdminUserEditForm(instance=user_obj)

    return render(request, 'accounts/admin_user_edit.html', {
        'form': form,
        'user_obj': user_obj,
    })

@admin_required
@require_POST
def admin_user_delete(request, pk):
    user_obj = get_object_or_404(Users, pk=pk)

    # Tidak boleh menghapus akun yang sedang digunakan.
    if user_obj.pk == request.user.pk:
        messages.error(
            request,
            'Kamu tidak dapat menghapus akunmu sendiri.'
        )
        return redirect('admin_user_detail', pk=user_obj.pk)

    # Lindungi akun superuser.
    if user_obj.is_superuser:
        messages.error(
            request,
            'Akun superuser tidak dapat dihapus melalui halaman ini.'
        )
        return redirect('admin_user_detail', pk=user_obj.pk)

    username = user_obj.username
    user_obj.delete()

    messages.success(
        request,
        f'Akun {username} berhasil dihapus.'
    )
    return redirect('admin_user_list')


def navbar_notifications(request):
    if not request.user.is_authenticated:
        return {
            'navbar_notifications': [],
            'navbar_unread_count': 0,
        }

    from .models import Activity

    activities = (
        Activity.objects
        .filter(recipient=request.user)
        .select_related(
            'actor',
            'article',
            'chapter',
            'chapter__story',
        )
        .order_by('-created_at')
    )

    return {
        'navbar_notifications': activities[:2],
        'navbar_unread_count': activities.filter(
            is_read=False
        ).count(),
    }


@login_required
def notifications_list(request):
    activities = (
        Activity.objects
        .filter(recipient=request.user)
        .select_related(
            'actor',
            'article',
            'chapter',
            'chapter__story',
        )
        .order_by('-created_at')
    )

    paginator = Paginator(activities, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'accounts/notifications_list.html',
        {
            'page_obj': page_obj,
            'breadcrumb': 'Notifikasi',
        }
    )

@login_required
def contributor_application_status(request):
    application = (
        ContributorApplication.objects
        .filter(user=request.user)
        .order_by('-submitted_at')
        .first()
    )

    if application is None:
        messages.info(
            request,
            'Kamu belum memiliki pengajuan kontributor.',
        )
        return redirect('apply_contributor')

    context = {
        'application': application,
        'publisher_id': request.user.publisher_id,
    }

    return render(
        request,
        'accounts/contributor_application_status.html',
        context,
    )


