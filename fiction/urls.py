from django.urls import path
from . import views

app_name = 'fiction'

urlpatterns = [
    path('tulis/', views.create_story, name='create_story'),
    path('milikku/', views.my_stories, name='my_stories'),
    path('tags/suggest/', views.tag_suggestions, name='tag_suggestions'),
    path('tag/<str:tag>/', views.tag_stories, name='tag_stories'),
    path('<int:pk>/edit/', views.edit_story, name='edit_story'),
    path('<int:pk>/favorite/', views.toggle_favorite_story, name='toggle_favorite_story'),
    path('<int:story_id>/bab/', views.chapter_list, name='chapter_list'),
    path('<int:story_id>/bab/tambah/', views.add_chapter, name='add_chapter'),
    path('<int:story_id>/bab/<int:chapter_id>/edit/', views.edit_chapter, name='edit_chapter'),
    path('<int:story_id>/bab/<int:chapter_id>/hapus/', views.delete_chapter, name='delete_chapter'),
    path('kelola/pending/', views.admin_pending_stories, name='admin_pending_stories'),
    path('kelola/<int:pk>/approve/', views.admin_approve_story, name='admin_approve_story'),
    path('kelola/<int:pk>/reject/', views.admin_reject_story, name='admin_reject_story'),
    path('kelola/<int:pk>/review/', views.admin_review_story, name='admin_review_story'),
    path('', views.story_list, name='story_list'),
    path('<int:pk>/', views.story_detail, name='story_detail'),
    path('<int:pk>/baca/<int:chapter_number>/', views.read_chapter, name='read_chapter'),
]