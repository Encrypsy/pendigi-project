from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView, admin_user_delete, admin_user_detail, admin_user_edit, admin_user_list, author_notifications, author_pending_content, author_rejected_content, notifications_list, register_view, apply_contributor, profile_view, dashboard_view, admin_pending_contributors, admin_approve_contributor, admin_reject_contributor, toggle_follow, author_dashboard, author_my_content

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='articles:article_list'), name='logout'),
    path('register/', register_view, name='register'),
    path('apply-kontributor/', apply_contributor, name='apply_contributor'),
    path('profile/', profile_view, name='profile'),
    path(
        'profile/<str:username>/',
        profile_view,
        name='public_profile',
    ),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/penulis/', author_dashboard, name='author_dashboard'),
    path('kelola/kontributor/', admin_pending_contributors, name='admin_pending_contributors'),
    path('kelola/kontributor/<int:pk>/approve/', admin_approve_contributor, name='admin_approve_contributor'),
    path('kelola/kontributor/<int:pk>/reject/', admin_reject_contributor, name='admin_reject_contributor'),
    path('follow/<str:username>/', toggle_follow, name='toggle_follow'),
    path('dashboard/penulis/konten/',author_my_content, name='author_my_content'),
    path('dashboard/penulis/pending/', author_pending_content, name='author_pending_content'),
    path('dashboard/penulis/ditolak/', author_rejected_content, name='author_rejected_content'),
    path('dashboard/penulis/notifikasi/', author_notifications, name='author_notifications'),
    path('kelola/user/', admin_user_list, name='admin_user_list'),
    path('kelola/user/<int:pk>/', admin_user_detail, name='admin_user_detail'),  
    path(
        'notifikasi/',
        notifications_list,
        name='notifications_list',
    ), 
    path(
        'kelola/user/<int:pk>/edit/',
        admin_user_edit,
        name='admin_user_edit',
    ),
    path(
        'kelola/user/<int:pk>/delete/',
        admin_user_delete,
        name='admin_user_delete',
    ),
]