from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import RegisterForm, ContributorApplicationForm, ProfileUpdateForm
from .models import StatusKontributor


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
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
def profile_view(request):
    favorites = request.user.favorite_articles.select_related('article').all()
    notes = request.user.personal_notes.select_related('article').all()[:10]
    activities = request.user.activities.select_related('article').all()[:15]

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
        'form': form,
        'published_count': published_count,
    })