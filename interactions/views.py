from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST
from articles.models import Articles
from .models import Activity, CommentDislikes, CommentLikes, Comments, Ratings, Bookmarks, StatusComment
from .forms import CommentForm, RatingForm
from reading_journal.models import ReadingActivity, ActionType
from accounts.decorators import admin_required
from django.db.models import Q
from django.core.paginator import Paginator


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
            parent_comment = get_object_or_404(
                Comments,
                pk=parent_id,
                article=article
            )
            comment.parent = parent_comment

        # Admin tidak perlu approval
        if request.user.role == 'admin' or request.user.is_superuser:
            comment.status = StatusComment.APPROVED

        comment.save()

        ReadingActivity.objects.create(
            user=request.user,
            article=article,
            action_type=ActionType.COMMENTED
        )
        
        print("DEBUG COMMENT STATUS:", comment.status)
        print("DEBUG ARTICLE CONTRIBUTOR:", article.contributor)
        print("DEBUG REQUEST USER:", request.user)

        # ==========================================
        # NOTIFIKASI AKTIVITAS UNTUK PENULIS
        # ==========================================

        if comment.status == StatusComment.APPROVED:
            
            print("DEBUG: MASUK KE ACTIVITY COMMENT")
            
            Activity.objects.create(
                recipient=article.contributor,
                actor=request.user,
                article=article,
                action_type=Activity.ActionType.COMMENT,
                message='Memberikan komentar',
            )
            
            print("DEBUG: ACTIVITY BERHASIL DIBUAT")

            messages.success(
                request,
                'Komentar berhasil dikirim.'
            )

        else:
            messages.success(
                request,
                'Komentar terkirim, menunggu approval admin.'
            )

    else:
        messages.error(
            request,
            'Komentar gagal dikirim, pastikan tidak kosong.'
        )

    return redirect(
        'articles:article_detail',
        pk=pk
    )


@login_required
@require_POST
def submit_rating(request, pk):
    """Use case: Beri rating & komentar artikel (bagian rating)"""
    article = get_object_or_404(Articles, pk=pk)
    form = RatingForm(request.POST)

    if form.is_valid():

        rating_value = form.cleaned_data['rating_value']

        rating, created = Ratings.objects.update_or_create(
            user=request.user,
            article=article,
            defaults={
                'rating_value': rating_value
            }
        )

        # ==========================================
        # NOTIFIKASI UNTUK PENULIS
        # ==========================================

        if created:
            Activity.objects.create(
                recipient=article.contributor,
                actor=request.user,
                article=article,
                action_type=Activity.ActionType.RATING,
                message=f"Memberikan rating {rating_value}/5 pada konten Anda",
            )

        ReadingActivity.objects.create(
            user=request.user,
            article=article,
            action_type=ActionType.RATED
        )

        messages.success(request, 'Rating tersimpan!')

    else:
        messages.error(request, 'Rating tidak valid.')

    return redirect(
        'articles:article_detail',
        pk=pk
    )


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

    edit_id = request.POST.get('edit_id')
    if edit_id:
        comment = get_object_or_404(Comments, pk=edit_id, user=request.user)
        comment.content = request.POST.get('content', comment.content)
        comment.save()
        if _is_ajax(request):
            return JsonResponse({'ok': True})
        return redirect('articles:article_detail', pk=pk)

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.article = article
        parent_id = request.POST.get('parent_id')
        if parent_id:
            comment.parent = get_object_or_404(Comments, pk=parent_id, article=article)
        if request.user.role == 'admin' or request.user.is_superuser:
            comment.status = StatusComment.APPROVED
        comment.save()
        if _is_ajax(request):
            return JsonResponse({'ok': True})
        return redirect('articles:article_detail', pk=pk)
    else:
        if _is_ajax(request):
            return JsonResponse({'error': 'Komentar tidak boleh kosong.'})
        messages.error(request, 'Komentar tidak boleh kosong.')
        return redirect('articles:article_detail', pk=pk)


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comments, pk=comment_id, user=request.user)
    article_pk = comment.article.pk
    comment.delete()
    if _is_ajax(request):
        return JsonResponse({'ok': True})
    return redirect('articles:article_detail', pk=article_pk)


@login_required
@require_POST
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comments, pk=comment_id)
    CommentDislikes.objects.filter(user=request.user, comment=comment).delete()
    like, created = CommentLikes.objects.get_or_create(user=request.user, comment=comment)
    if not created:
        like.delete()
    if _is_ajax(request):
        return JsonResponse({'ok': True})
    return redirect('articles:article_detail', pk=comment.article.pk)


@login_required
@require_POST
def toggle_comment_dislike(request, comment_id):
    comment = get_object_or_404(Comments, pk=comment_id)
    CommentLikes.objects.filter(user=request.user, comment=comment).delete()
    dislike, created = CommentDislikes.objects.get_or_create(user=request.user, comment=comment)
    if not created:
        dislike.delete()
    if _is_ajax(request):
        return JsonResponse({'ok': True})
    return redirect('articles:article_detail', pk=comment.article.pk)

@admin_required
def admin_comment_approval(request, status='pending'):

    allowed_statuses = {
        'pending': StatusComment.PENDING,
        'approved': StatusComment.APPROVED,
        'rejected': StatusComment.REJECTED,
    }

    if status not in allowed_statuses:
        return redirect('interactions:admin_comment_approval')


    # =========================
    # DATA KOMENTAR
    # =========================

    comments = Comments.objects.filter(
        status=allowed_statuses[status]
    ).select_related(
        'user',
        'article'
    )


    # =========================
    # SEARCH
    # =========================

    query = request.GET.get('q', '').strip()

    if query:
        comments = comments.filter(
            Q(content__icontains=query) |
            Q(user__username__icontains=query) |
            Q(article__title__icontains=query)
        )


    # =========================
    # URUTAN
    # =========================

    comments = comments.order_by('-created_at')


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

    paginator = Paginator(comments, per_page)

    page_number = request.GET.get('page', 1)

    page_obj = paginator.get_page(page_number)


    # =========================
    # JUMLAH PER STATUS
    # =========================

    status_counts = {
        'pending': Comments.objects.filter(
            status=StatusComment.PENDING
        ).count(),

        'approved': Comments.objects.filter(
            status=StatusComment.APPROVED
        ).count(),

        'rejected': Comments.objects.filter(
            status=StatusComment.REJECTED
        ).count(),
    }


    # =========================
    # RENDER
    # =========================

    return render(
        request,
        'interactions/admin_comment_approval.html',
        {
            'comments': page_obj.object_list,

            # pagination
            'page_obj': page_obj,
            'per_page': per_page,
            'per_page_options': [10, 25, 50],

            # search
            'search_query': query,

            # status
            'comment_status': status,
            'status_counts': status_counts,
        }
    )

@admin_required
@require_POST
def admin_approve_comment(request, pk):

    comment = get_object_or_404(Comments, pk=pk)

    comment.status = StatusComment.APPROVED
    comment.save()

    messages.success(
        request,
        'Komentar berhasil disetujui.'
    )

    return redirect(
        'interactions:admin_comment_approval_status',
        status='pending'
    )


@admin_required
@require_POST
def admin_reject_comment(request, pk):

    comment = get_object_or_404(Comments, pk=pk)

    comment.status = StatusComment.REJECTED
    comment.save()

    messages.success(
        request,
        'Komentar berhasil ditolak.'
    )

    return redirect(
        'interactions:admin_comment_approval_status',
        status='pending'
    )

def _attach_comment_meta(comments, request, like_url_name, dislike_url_name, url_kwargs, post_url=None):
    result = []
    for c in comments:
        c.is_owner = request.user.is_authenticated and c.user_id == request.user.id
        c.is_liked = request.user.is_authenticated and c.likes.filter(user=request.user).exists()
        c.is_disliked = request.user.is_authenticated and c.dislikes.filter(user=request.user).exists()
        c.like_url = reverse(like_url_name, kwargs={**url_kwargs, 'comment_id': c.pk})
        c.dislike_url = reverse(dislike_url_name, kwargs={**url_kwargs, 'comment_id': c.pk})
        c.edit_url = post_url
        c.delete_url = reverse('interactions:delete_comment', kwargs={'comment_id': c.pk}) if c.is_owner else None

        replies = list(c.get_all_replies())
        for r in replies:
            r.is_owner = request.user.is_authenticated and r.user_id == request.user.id
            r.is_liked = request.user.is_authenticated and r.likes.filter(user=request.user).exists()
            r.parent_username = r.parent.user.username
            r.like_url = reverse(like_url_name, kwargs={**url_kwargs, 'comment_id': r.pk})
        c.reply_list = replies
        result.append(c)
    return result


def _sort_comments(queryset, sort):
    if sort == 'oldest':
        return queryset.order_by('created_at')
    if sort == 'liked':
        return sorted(queryset, key=lambda c: c.likes.count(), reverse=True)
    return queryset.order_by('-created_at')

def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'
