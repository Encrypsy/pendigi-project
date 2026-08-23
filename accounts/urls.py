from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView, register_view, apply_contributor, profile_view, dashboard_view, admin_pending_contributors, admin_approve_contributor, admin_reject_contributor

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='articles:article_list'), name='logout'),
    path('register/', register_view, name='register'),
    path('apply-kontributor/', apply_contributor, name='apply_contributor'),
    path('profile/', profile_view, name='profile'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('kelola/kontributor/', admin_pending_contributors, name='admin_pending_contributors'),
    path('kelola/kontributor/<int:pk>/approve/', admin_approve_contributor, name='admin_approve_contributor'),
    path('kelola/kontributor/<int:pk>/reject/', admin_reject_contributor, name='admin_reject_contributor'),
]