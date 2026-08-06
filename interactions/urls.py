from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path('artikel/<int:pk>/komentar/', views.submit_comment, name='submit_comment'),
    path('artikel/<int:pk>/rating/', views.submit_rating, name='submit_rating'),
    path('artikel/<int:pk>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('bookmark-saya/', views.my_bookmarks, name='my_bookmarks'),
]