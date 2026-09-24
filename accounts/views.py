from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from .forms import RegisterForm, ContributorApplicationForm, ProfileUpdateForm
from .models import StatusKontributor, ContributorApplication, Users
from .decorators import admin_required
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from articles.models import Articles, StatusArticle, Categories
from interactions.models import Comments, StatusComment, Ratings
from articles.models import Articles, StatusArticle, Categories
from fiction.models import Stories, StatusStory as FictionStatusStory
from reading_journal.models import ReadingActivity
from datetime import timedelta
from django.views.decorators.http import require_POST
from .models import Follow
import json
from django.db.models.functions import TruncDate

@login_required
@require_POST
def toggle_follow(request, username):
    target_user = get_object_or_404(Users, username=username)

    if target_user == request.user:
        messages.error(request, 'Tidak bisa follow diri sendiri.')
        return redirect(request.META.get('HTTP_REFERER', 'articles:article_list'))

    follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)

    if not created:
        follow.delete()
        messages.info(request, f'Berhenti mengikuti {target_user.username}.')
    else:
        messages.success(request, f'Mengikuti {target_user.username}.')

    return redirect(request.META.get('HTTP_REFERER', 'articles:article_list'))


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
    if request.user.status_kontributor == StatusKontributor.APPROVED:
        messages.info(request, 'Anda sudah menjadi kontributor.')
        return redirect('articles:article_list')

    if request.user.status_kontributor == StatusKontributor.PENDING:
        messages.info(request, 'Pengajuan kamu masih menunggu verifikasi admin.')
        return redirect('articles:article_list')

    if request.method == 'POST':
        form = ContributorApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.status = StatusKontributor.PENDING
            application.save()

            request.user.status_kontributor = StatusKontributor.PENDING
            request.user.save()

            messages.success(request, 'Pengajuan terkirim! Menunggu verifikasi admin.')
            return redirect('articles:article_list')
    else:
        form = ContributorApplicationForm()

    return render(request, 'accounts/apply_contributor.html', {'form': form})

@login_required
@login_required
def profile_view(request):
    favorites = request.user.favorite_articles.select_related('article').all()
    notes = request.user.personal_notes.select_related('article').all()[:10]
    activities = request.user.activities.select_related('article').all()[:15]
    stories = request.user.stories.all()[:5]

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil berhasil diperbarui!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    published_count = request.user.articles.filter(status='approved').count() if request.user.status_kontributor == 'approved' else None

    return render(request, 'accounts/profile.html', {
        'favorites': favorites,
        'notes': notes,
        'activities': activities,
        'stories': stories,
        'form': form,
        'published_count': published_count,
    })

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

@admin_required
def admin_pending_contributors(request):
    applications = ContributorApplication.objects.filter(
        status=StatusKontributor.PENDING
    ).select_related('user')
    return render(request, 'accounts/admin_pending_contributors.html', {'applications': applications})


@admin_required
@require_POST
def admin_approve_contributor(request, pk):
    application = get_object_or_404(ContributorApplication, pk=pk)
    application.status = StatusKontributor.APPROVED
    application.save()

    application.user.status_kontributor = StatusKontributor.APPROVED
    application.user.save()

    messages.success(request, f'{application.user.username} disetujui sebagai kontributor.')
    return redirect('admin_pending_contributors')


@admin_required
@require_POST
def admin_reject_contributor(request, pk):
    application = get_object_or_404(ContributorApplication, pk=pk)
    application.status = StatusKontributor.REJECTED
    application.save()

    application.user.status_kontributor = StatusKontributor.REJECTED
    application.user.save()

    messages.success(request, f'Pengajuan {application.user.username} ditolak.')
    return redirect('admin_pending_contributors')