from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from articles.models import Articles
from .models import Comments, Ratings, Bookmarks, StatusComment
from .forms import CommentForm, RatingForm
from reading_journal.models import ReadingActivity, ActionType
from accounts.decorators import admin_required


@login_required
@require_POST
def submit_comment(request, pk):
    article = get_object_or_404(Articles, pk=pk)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.article = article

        parent_id = request.POST.get('parent_id')
        if parent_id:
            parent_comment = get_object_or_404(Comments, pk=parent_id, article=article)
            comment.parent = parent_comment

        # Admin nggak perlu approval buat komentar sendiri
        if request.user.role == 'admin' or request.user.is_superuser:
            comment.status = StatusComment.APPROVED
        

        comment.save()

        ReadingActivity.objects.create(user=request.user, article=article, action_type=ActionType.COMMENTED)
        
        if comment.status == StatusComment.APPROVED:
            messages.success(request, 'Komentar berhasil dikirim.')
        else:
            messages.success(request, 'Komentar terkirim, menunggu approval admin.')
    else:
        messages.error(request, 'Komentar gagal dikirim, pastikan tidak kosong.')

    return redirect('articles:article_detail', pk=pk)


@login_required
@require_POST
def submit_rating(request, pk):
    """Use case: Beri rating & komentar artikel (bagian rating)"""
    article = get_object_or_404(Articles, pk=pk)
    form = RatingForm(request.POST)

    if form.is_valid():
        Ratings.objects.update_or_create(
            user=request.user, article=article,
            defaults={'rating_value': form.cleaned_data['rating_value']}
        )
        ReadingActivity.objects.create(user=request.user, article=article, action_type=ActionType.RATED)
        messages.success(request, 'Rating tersimpan!')
    else:
        messages.error(request, 'Rating tidak valid.')

    return redirect('articles:article_detail', pk=pk)


@login_required
@require_POST
def toggle_bookmark(request, pk):
    """Use case: Simpan/bookmark artikel"""
    article = get_object_or_404(Articles, pk=pk)
    bookmark, created = Bookmarks.objects.get_or_create(user=request.user, article=article)

    if not created:
        bookmark.delete()
        messages.info(request, 'Artikel dihapus dari bookmark.')
    else:
        ReadingActivity.objects.create(user=request.user, article=article, action_type=ActionType.BOOKMARKED)
        messages.success(request, 'Artikel disimpan ke bookmark.')

    return redirect('articles:article_detail', pk=pk)


@login_required
def my_bookmarks(request):
    bookmarks = request.user.bookmarks.select_related('article').all()
    return render(request, 'interactions/bookmarks.html', {'bookmarks': bookmarks})

@login_required
@require_POST
def submit_comment(request, pk):
    article = get_object_or_404(Articles, pk=pk)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.article = article

        parent_id = request.POST.get('parent_id')
        if parent_id:
            parent_comment = get_object_or_404(Comments, pk=parent_id, article=article)
            comment.parent = parent_comment

        comment.save()

        ReadingActivity.objects.create(user=request.user, article=article, action_type=ActionType.COMMENTED)
        messages.success(request, 'Komentar terkirim, menunggu approval admin.')
    else:
        messages.error(request, 'Komentar gagal dikirim, pastikan tidak kosong.')

    return redirect('articles:article_detail', pk=pk)

@admin_required
def admin_pending_comments(request):
    comments = Comments.objects.filter(status=StatusComment.PENDING).select_related('user', 'article')
    return render(request, 'interactions/admin_pending.html', {'comments': comments})


@admin_required
@require_POST
def admin_approve_comment(request, pk):
    comment = get_object_or_404(Comments, pk=pk)
    comment.status = StatusComment.APPROVED
    comment.save()
    messages.success(request, 'Komentar disetujui.')
    return redirect('interactions:admin_pending_comments')


@admin_required
@require_POST
def admin_reject_comment(request, pk):
    comment = get_object_or_404(Comments, pk=pk)
    comment.status = StatusComment.REJECTED
    comment.save()
    messages.success(request, 'Komentar ditolak.')
    return redirect('interactions:admin_pending_comments')