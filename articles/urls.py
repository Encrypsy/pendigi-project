from django.urls import path
from . import views

app_name = 'articles'

urlpatterns = [
    path('', views.article_list, name='article_list'),
    path('upload/', views.upload_article, name='upload_article'),
    path('milikku/', views.my_articles, name='my_articles'),
    path('<int:pk>/', views.article_detail, name='article_detail'),
    path('<int:pk>/selesai/', views.mark_as_finished, name='mark_as_finished'),
    path('<int:pk>/edit/', views.edit_article, name='edit_article'),
    path('<int:pk>/delete/', views.delete_article, name='delete_article'),
    path('<int:pk>/komentar-partial/', views.article_comments_partial, name='article_comments_partial'),
    path('kelola/pending/', views.admin_pending_articles, name='admin_pending_articles'),
    path('kelola/<int:pk>/approve/', views.admin_approve_article, name='admin_approve_article'),
    path('kelola/<int:pk>/reject/', views.admin_reject_article, name='admin_reject_article'),
    path('kelola/kategori/', views.category_list, name='category_list'),
    path('kelola/kategori/tambah/', views.category_create, name='category_create'),
    path('kelola/kategori/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('kelola/kategori/<int:pk>/hapus/', views.category_delete, name='category_delete'),
    path('kelola/banner/', views.banner_list, name='banner_list'),
    path('kelola/banner/tambah/', views.banner_create, name='banner_create'),
    path('kelola/banner/<int:pk>/hapus/', views.banner_delete, name='banner_delete'),
    path('kelola/banner/<int:pk>/toggle/', views.banner_toggle_active, name='banner_toggle_active'),
    path('kelola/banner/preview/', views.banner_preview, name='banner_preview'),
]