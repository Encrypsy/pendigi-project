from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path('artikel/<int:pk>/komentar/', views.submit_comment, name='submit_comment'),
    path('artikel/<int:pk>/rating/', views.submit_rating, name='submit_rating'),
    path('artikel/<int:pk>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('bookmark-saya/', views.my_bookmarks, name='my_bookmarks'),
    path('kelola/pending/', views.admin_pending_comments, name='admin_pending_comments'),
    path('kelola/<int:pk>/approve/', views.admin_approve_comment, name='admin_approve_comment'),
    path('kelola/<int:pk>/reject/', views.admin_reject_comment, name='admin_reject_comment'),
]