from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path(
        'artikel/<int:pk>/komentar/',
        views.submit_comment,
        name='submit_comment'
    ),

    path(
        'artikel/<int:pk>/rating/',
        views.submit_rating,
        name='submit_rating'
    ),

    path(
        'artikel/<int:pk>/bookmark/',
        views.toggle_bookmark,
        name='toggle_bookmark'
    ),

    path(
        'bookmark-saya/',
        views.my_bookmarks,
        name='my_bookmarks'
    ),

        # =========================
    # COMMENT APPROVAL
    # =========================

    path(
        'kelola/approval-komentar/',
        views.admin_comment_approval,
        name='admin_comment_approval'
    ),

    path(
        'kelola/approval-komentar/<str:status>/',
        views.admin_comment_approval,
        name='admin_comment_approval_status'
    ),

    path(
        'kelola/<str:comment_type>/<int:pk>/approve/',
        views.admin_approve_comment,
        name='admin_approve_comment'
    ),

    path(
        'kelola/<str:comment_type>/<int:pk>/reject/',
        views.admin_reject_comment,
        name='admin_reject_comment'
    ),

    path(
        'kelola/<str:comment_type>/<int:pk>/hapus/',
        views.admin_delete_comment,
        name='admin_delete_comment'
    ),

    path(
        'komentar/<int:comment_id>/like/',
        views.toggle_comment_like,
        name='toggle_comment_like'
    ),

    path(
        'komentar/<int:comment_id>/dislike/',
        views.toggle_comment_dislike,
        name='toggle_comment_dislike'
    ),
    path(
        'notifikasi/tandai-dibaca/',
        views.mark_notifications_read,
        name='mark_notifications_read',
    ),   
    path(
        'fiksi/<int:pk>/bookmark/',
        views.toggle_story_bookmark,
        name='toggle_story_bookmark',
    ),
    path(
        'artikel/<int:pk>/like/',
        views.toggle_article_like,
        name='toggle_article_like'
    ),

    path(
        'fiksi/<int:pk>/like/',
        views.toggle_story_like,
        name='toggle_story_like'
    ),
    path(
        'konten-disukai/',
        views.my_likes,
        name='my_likes',
    ),
]