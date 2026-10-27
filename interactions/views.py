
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme

from articles.models import Articles, StatusArticle
from fiction.models import Stories
from .models import (
    Activity,
    CommentDislikes,
    CommentLikes,
    Comments,
    Ratings,
    Bookmarks,
    StatusComment,
)
from .forms import CommentForm, RatingForm
from reading_journal.models import ReadingActivity, ActionType
from accounts.decorators import admin_required


def _is_ajax(request):
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


@login_required
@require_POST
def submit_comment(request, pk):
    article = get_object_or_404(Articles, pk=pk)

    is_ajax = _is_ajax(request)

    def respond(success, message, http_status=200, **extra):
        if is_ajax:
            data = {
                'ok': success,
                'success': success,
                'message': message,
                **extra,
            }
            return JsonResponse(data, status=http_status)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('articles:article_detail', pk=pk)

    # Edit komentar milik pengguna yang sedang login.
    edit_id = request.POST.get("edit_id")
    if edit_id:
        comment = get_object_or_404(
            Comments,
            pk=edit_id,
            user=request.user,
            article=article,
        )

        form = CommentForm(request.POST, instance=comment)
        if not form.is_valid():
            return respond(
                False,
                "Komentar gagal diperbarui. Periksa kembali isinya.",
                status=400,
            )

        updated_comment = form.save(commit=False)
        updated_comment.save()

        return respond(
            True,
            "Komentar berhasil diperbarui.",
            comment_id=updated_comment.pk,
            parent_id=updated_comment.parent_id,
            content=updated_comment.content,
            username=request.user.username,
            status=updated_comment.status,
        )

    form = CommentForm(request.POST)

    if not form.is_valid():
        return respond(
            False,
            "Komentar gagal dikirim. Pastikan isinya tidak kosong.",
            status=400,
        )

    comment = form.save(commit=False)
    comment.user = request.user
    comment.article = article

    parent_id = request.POST.get("parent_id", "").strip()
    parent_comment = None

    if parent_id:
        parent_comment = get_object_or_404(
            Comments,
            pk=parent_id,
            article=article,
            parent__isnull=True,
            status=StatusComment.APPROVED,
        )
        comment.parent = parent_comment

    is_admin = (
        getattr(request.user, "role", None) == "admin"
        or request.user.is_superuser
    )

    if is_admin:
        comment.status = StatusComment.APPROVED

    comment.save()

    ReadingActivity.objects.create(
        user=request.user,
        article=article,
        action_type=ActionType.COMMENTED,
    )

    # Notifikasi hanya dikirim untuk komentar yang sudah disetujui.
    if comment.status == StatusComment.APPROVED:
        if parent_comment:
            if parent_comment.user_id != request.user.id:
                Activity.objects.create(
                    recipient=parent_comment.user,
                    actor=request.user,
                    article=article,
                    action_type=Activity.ActionType.COMMENT_REPLY,
                    message=(
                        f'Membalas komentar Anda pada artikel '
                        f'"{article.title}".'
                    )[:255],
                )
        elif article.contributor_id != request.user.id:
            Activity.objects.create(
                recipient=article.contributor,
                actor=request.user,
                article=article,
                action_type=Activity.ActionType.COMMENT,
                message=(
                    f'Memberikan komentar pada artikel '
                    f'"{article.title}".'
                )[:255],
            )

    if comment.status == StatusComment.APPROVED:
        message = (
            "Balasan berhasil dikirim."
            if parent_comment
            else "Komentar berhasil dikirim."
        )
    else:
        message = "Komentar terkirim dan menunggu persetujuan admin."

    return respond(
        True,
        'Komentar terkirim dan menunggu approval admin.',
        comment_id=comment.pk,
        parent_id=comment.parent_id,
        content=comment.content,
        username=request.user.username,
        status=comment.status,
    )


@login_required
@require_POST
def submit_rating(request, pk):
    article = get_object_or_404(
        Articles,
        pk=pk,
        status=StatusArticle.APPROVED,
    )

    form = RatingForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Rating tidak valid.")
        return redirect("articles:article_detail", pk=pk)

    rating_value = form.cleaned_data["rating_value"]

    rating, created = Ratings.objects.update_or_create(
        user=request.user,
        article=article,
        defaults={"rating_value": rating_value},
    )

    if created and article.contributor_id != request.user.id:
        Activity.objects.create(
            recipient=article.contributor,
            actor=request.user,
            article=article,
            action_type=Activity.ActionType.RATING,
            message=(
                f"Memberikan rating {rating_value}/5 "
                f"pada konten Anda"
            )[:255],
        )

    ReadingActivity.objects.get_or_create(
        user=request.user,
        article=article,
        action_type=ActionType.RATED,
    )

    messages.success(
        request,
        "Rating berhasil disimpan!"
        if created
        else "Rating berhasil diperbarui!",
    )

    return redirect("articles:article_detail", pk=pk)



@login_required
@require_POST
def toggle_bookmark(request, pk):
    article = get_object_or_404(Articles, pk=pk)

    bookmark, created = Bookmarks.objects.get_or_create(
        user=request.user,
        article=article,
    )

    if not created:
        bookmark.delete()
        messages.info(request, "Artikel dihapus dari bookmark.")
    else:
        ReadingActivity.objects.get_or_create(
            user=request.user,
            article=article,
            action_type=ActionType.BOOKMARKED,
        )
        messages.success(request, "Artikel disimpan ke bookmark.")

    return redirect("articles:article_detail", pk=pk)


@login_required
def my_bookmarks(request):
    bookmarks = request.user.bookmarks.select_related("article").all()

    return render(
        request,
        "interactions/bookmarks.html",
        {
            "bookmarks": bookmarks,
        },
    )


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(
        Comments,
        pk=comment_id,
        user=request.user,
    )
    article_pk = comment.article_id
    comment.delete()

    if _is_ajax(request):
        return JsonResponse({"ok": True})

    return redirect("articles:article_detail", pk=article_pk)


@login_required
@require_POST
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comments, pk=comment_id)

    CommentDislikes.objects.filter(
        user=request.user,
        comment=comment,
    ).delete()

    like, created = CommentLikes.objects.get_or_create(
        user=request.user,
        comment=comment,
    )

    if not created:
        like.delete()
    elif comment.user_id != request.user.id:
        Activity.objects.create(
            recipient=comment.user,
            actor=request.user,
            article=comment.article,
            action_type=Activity.ActionType.LIKE,
            message=(
                f'Menyukai komentar Anda: '
                f'"{comment.content[:80]}" '
                f'pada artikel "{comment.article.title}".'
            )[:255],
        )

    if _is_ajax(request):
        return JsonResponse({"ok": True})

    return redirect("articles:article_detail", pk=comment.article.pk)


@login_required
@require_POST
def toggle_comment_dislike(request, comment_id):
    comment = get_object_or_404(Comments, pk=comment_id)

    CommentLikes.objects.filter(
        user=request.user,
        comment=comment,
    ).delete()

    dislike, created = CommentDislikes.objects.get_or_create(
        user=request.user,
        comment=comment,
    )

    if not created:
        dislike.delete()

    if _is_ajax(request):
        return JsonResponse({"ok": True})

    return redirect("articles:article_detail", pk=comment.article.pk)


@admin_required
def admin_comment_approval(request, status="pending"):
    allowed_statuses = {
        "pending": StatusComment.PENDING,
        "approved": StatusComment.APPROVED,
        "rejected": StatusComment.REJECTED,
    }

    if status not in allowed_statuses:
        return redirect("interactions:admin_comment_approval")

    comments = Comments.objects.filter(
        status=allowed_statuses[status]
    ).select_related(
        "user",
        "article",
    )

    query = request.GET.get("q", "").strip()

    if query:
        comments = comments.filter(
            Q(content__icontains=query)
            | Q(user__username__icontains=query)
            | Q(article__title__icontains=query)
        )

    comments = comments.order_by("-created_at")

    try:
        per_page = int(request.GET.get("per_page", 10))
        if per_page not in (10, 25, 50):
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10

    paginator = Paginator(comments, per_page)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    status_counts = {
        "pending": Comments.objects.filter(
            status=StatusComment.PENDING
        ).count(),
        "approved": Comments.objects.filter(
            status=StatusComment.APPROVED
        ).count(),
        "rejected": Comments.objects.filter(
            status=StatusComment.REJECTED
        ).count(),
    }

    return render(
        request,
        "interactions/admin_comment_approval.html",
        {
            "comments": page_obj.object_list,
            "page_obj": page_obj,
            "per_page": per_page,
            "per_page_options": [10, 25, 50],
            "search_query": query,
            "comment_status": status,
            "status_counts": status_counts,
        },
    )


@admin_required
@require_POST
def admin_approve_comment(request, pk):
    comment = get_object_or_404(Comments, pk=pk)

    comment.status = StatusComment.APPROVED
    comment.save()

    # Untuk komentar utama, beri tahu penulis artikel.
    # Untuk balasan, beri tahu pemilik komentar yang dibalas.
    if comment.parent_id:
        recipient = comment.parent.user
        action_type = Activity.ActionType.COMMENT_REPLY
        message = (
            f'Balasan Anda pada artikel "{comment.article.title}" '
            "telah disetujui."
        )
    else:
        recipient = comment.article.contributor
        action_type = Activity.ActionType.COMMENT
        message = (
            f'Komentar baru pada artikel "{comment.article.title}".'
        )

    if recipient and recipient.pk != comment.user_id:
        Activity.objects.create(
            recipient=recipient,
            actor=comment.user,
            article=comment.article,
            action_type=action_type,
            message=message[:255],
        )

    messages.success(request, "Komentar berhasil disetujui.")

    return redirect(
        "interactions:admin_comment_approval_status",
        status="pending",
    )


@admin_required
@require_POST
def admin_reject_comment(request, pk):
    comment = get_object_or_404(Comments, pk=pk)

    comment.status = StatusComment.REJECTED
    comment.save()

    messages.success(request, "Komentar berhasil ditolak.")

    return redirect(
        "interactions:admin_comment_approval_status",
        status="pending",
    )

@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(
        Comments.objects.select_related('user', 'article'),
        pk=comment_id,
    )

    is_admin = (
        request.user.is_staff
        or request.user.is_superuser
        or getattr(request.user, 'role', '') == 'admin'
    )

    # Pengguna biasa hanya boleh menghapus komentar sendiri.
    if comment.user_id != request.user.pk and not is_admin:
        messages.error(
            request,
            'Kamu hanya dapat menghapus komentar milikmu sendiri.',
        )
        return redirect('articles:article_list')
    
    # Simpan URL tujuan sebelum menghapus komentar.
    next_url = request.POST.get('next', '')
    article_id = comment.article_id
    comment.delete()

    messages.success(request, 'Komentar berhasil dihapus.')

    # Kembali ke halaman asal hanya jika URL aman dan berasal dari host sendiri.
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect('articles:article_list')

def _attach_comment_meta(
    comments,
    request,
    like_url_name,
    dislike_url_name,
    url_kwargs,
    post_url=None,
):
    result = []

    for comment in comments:
        comment.is_owner = (
            request.user.is_authenticated
            and comment.user_id == request.user.id
        )
        comment.is_liked = (
            request.user.is_authenticated
            and comment.likes.filter(user=request.user).exists()
        )
        comment.is_disliked = (
            request.user.is_authenticated
            and comment.dislikes.filter(user=request.user).exists()
        )

        comment.like_url = reverse(
            like_url_name,
            kwargs={**url_kwargs, "comment_id": comment.pk},
        )
        comment.dislike_url = reverse(
            dislike_url_name,
            kwargs={**url_kwargs, "comment_id": comment.pk},
        )
        comment.edit_url = post_url
        comment.delete_url = (
            reverse(
                "interactions:delete_comment",
                kwargs={"comment_id": comment.pk},
            )
            if comment.is_owner
            else None
        )

        replies = [
            reply
            for reply in comment.get_all_replies()
            if reply.status == StatusComment.APPROVED
        ]

        for reply in replies:
            reply.is_owner = (
                request.user.is_authenticated
                and reply.user_id == request.user.id
            )
            reply.is_liked = (
                request.user.is_authenticated
                and reply.likes.filter(user=request.user).exists()
            )
            reply.is_disliked = (
                request.user.is_authenticated
                and reply.dislikes.filter(user=request.user).exists()
            )
            reply.parent_username = reply.parent.user.username
            reply.like_url = reverse(
                like_url_name,
                kwargs={**url_kwargs, "comment_id": reply.pk},
            )
            reply.dislike_url = reverse(
                dislike_url_name,
                kwargs={**url_kwargs, "comment_id": reply.pk},
            )
            reply.edit_url = post_url
            reply.delete_url = (
                reverse(
                    "interactions:delete_comment",
                    kwargs={"comment_id": reply.pk},
                )
                if reply.is_owner
                else None
            )

        comment.reply_list = replies
        result.append(comment)

    return result


def _sort_comments(queryset, sort):
    if sort == "oldest":
        return queryset.order_by("created_at")

    if sort == "liked":
        return sorted(
            queryset,
            key=lambda comment: comment.likes.count(),
            reverse=True,
        )

    return queryset.order_by("-created_at")


@login_required
@require_POST
def mark_notifications_read(request):
    Activity.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    return JsonResponse({"success": True, "ok": True})

def _bookmark_redirect(request, fallback='articles:article_list'):
    next_url = request.POST.get('next', '')

    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect(fallback)

@login_required
@require_POST
def toggle_bookmark(request, pk):
    article = get_object_or_404(Articles, pk=pk)

    bookmark, created = Bookmarks.objects.get_or_create(
        user=request.user,
        article=article,
    )

    bookmarked = created

    if not created:
        bookmark.delete()
        bookmarked = False

    # Jika request berasal dari AJAX, jangan redirect halaman
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'bookmarked': bookmarked,
            'message': (
                'Artikel berhasil disimpan.'
                if bookmarked
                else 'Artikel dihapus dari bookmark.'
            ),
        })

    # Tetap mendukung form biasa
    messages.success(
        request,
        'Artikel berhasil disimpan.'
        if bookmarked
        else 'Artikel dihapus dari bookmark.'
    )

    return _bookmark_redirect(request)


@login_required
@require_POST
def toggle_story_bookmark(request, pk):
    story = get_object_or_404(Stories, pk=pk)

    bookmark, created = Bookmarks.objects.get_or_create(
        user=request.user,
        story=story,
        article__isnull=True,
    )

    is_bookmarked = created

    if not created:
        bookmark.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_bookmarked': is_bookmarked,
            'message': (
                'Cerita berhasil disimpan.'
                if is_bookmarked
                else 'Cerita dihapus dari bookmark.'
            ),
        })

    if is_bookmarked:
        messages.success(request, 'Cerita berhasil disimpan.')
    else:
        messages.success(request, 'Cerita dihapus dari bookmark.')

    return _bookmark_redirect(request, fallback='fiction:story_list')


@login_required
def my_bookmarks(request):
    bookmarks = (
        Bookmarks.objects
        .filter(user=request.user)
        .select_related('article', 'story')
        .order_by('-created_at')
    )

    # Statistik seluruh bookmark, tidak terpengaruh pencarian
    total_bookmarks = bookmarks.count()
    total_articles = bookmarks.filter(article__isnull=False).count()
    total_stories = bookmarks.filter(story__isnull=False).count()

    # Ambil parameter dari URL
    active_tab = request.GET.get('tab', 'semua')
    search_query = request.GET.get('q', '').strip()
    sort_order = request.GET.get('sort', 'terbaru')

    # Validasi parameter
    if active_tab not in ('semua', 'artikel', 'fiksi'):
        active_tab = 'semua'

    if sort_order not in ('terbaru', 'terlama'):
        sort_order = 'terbaru'

    # Cari berdasarkan judul artikel atau cerita
    if search_query:
        bookmarks = bookmarks.filter(
            Q(article__title__icontains=search_query)
            | Q(story__title__icontains=search_query)
        )

    # Urutkan berdasarkan waktu bookmark disimpan
    if sort_order == 'terlama':
        bookmarks = bookmarks.order_by('created_at')
    else:
        bookmarks = bookmarks.order_by('-created_at')

    # Pisahkan artikel dan fiksi
    article_bookmarks = bookmarks.filter(
        article__isnull=False
    )

    story_bookmarks = bookmarks.filter(
        story__isnull=False
    )

    # Terapkan filter tab
    if active_tab == 'artikel':
        story_bookmarks = story_bookmarks.none()
    elif active_tab == 'fiksi':
        article_bookmarks = article_bookmarks.none()

    return render(
        request,
        'interactions/my_bookmarks.html',
        {
            'article_bookmarks': article_bookmarks,
            'story_bookmarks': story_bookmarks,
            'total_bookmarks': total_bookmarks,
            'total_articles': total_articles,
            'total_stories': total_stories,
            'active_tab': active_tab,
            'sort_order': sort_order,
            'search_query': search_query,
        },
    )
    
@login_required
@require_POST
def toggle_story_bookmark(request, pk):
    story = get_object_or_404(Stories, pk=pk)

    bookmark = Bookmarks.objects.filter(
        user=request.user,
        story=story,
        article__isnull=True,
    )

    if bookmark.exists():
        bookmark.delete()
        messages.success(request, 'Cerita dihapus dari bookmark.')
    else:
        Bookmarks.objects.create(
            user=request.user,
            story=story,
        )
        messages.success(request, 'Cerita berhasil disimpan.')

    next_url = request.POST.get('next', '')

    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect('articles:article_list')
