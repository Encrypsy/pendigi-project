from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from articles.models import Articles
from .models import PersonalNotes, FavoriteArticles
from .forms import PersonalNoteForm


@login_required
def add_note(request, article_id):
    """Target dari <<include>>: Isi catatan pribadi/insight"""
    article = get_object_or_404(Articles, pk=article_id)

    if request.method == 'POST':
        form = PersonalNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.article = article
            note.save()
            messages.success(request, 'Catatan tersimpan!')
            return redirect('articles:article_detail', pk=article_id)
    else:
        form = PersonalNoteForm()

    return render(request, 'reading_journal/add_note.html', {'form': form, 'article': article})


@login_required
def toggle_favorite(request, pk):
    """Use case: Kelola profil & top 4 artikel favorit"""
    article = get_object_or_404(Articles, pk=pk)
    existing = FavoriteArticles.objects.filter(user=request.user, article=article).first()

    if existing:
        existing.delete()
        messages.info(request, 'Dihapus dari artikel favorit.')
        return redirect('articles:article_detail', pk=pk)

    current_count = FavoriteArticles.objects.filter(user=request.user).count()
    if current_count >= 4:
        messages.error(request, 'Maksimal 4 artikel favorit. Hapus salah satu dulu.')
        return redirect('articles:article_detail', pk=pk)

    next_rank = current_count + 1
    FavoriteArticles.objects.create(user=request.user, article=article, rank_order=next_rank)
    messages.success(request, f'Ditambahkan sebagai favorit #{next_rank}.')
    return redirect('articles:article_detail', pk=pk)