from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView, register_view, apply_contributor, profile_view

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='articles:article_list'), name='logout'),
    path('register/', register_view, name='register'),
    path('apply-kontributor/', apply_contributor, name='apply_contributor'),
    path('profile/', profile_view, name='profile'),
]