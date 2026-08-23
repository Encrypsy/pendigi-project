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
    path('kelola/pending/', views.admin_pending_articles, name='admin_pending_articles'),
    path('kelola/<int:pk>/approve/', views.admin_approve_article, name='admin_approve_article'),
    path('kelola/<int:pk>/reject/', views.admin_reject_article, name='admin_reject_article'),
]