from django.urls import path
from . import views

app_name = 'reading_journal'

urlpatterns = [
    path('catatan/<int:article_id>/', views.add_note, name='add_note'),
    path('favorit/<int:pk>/toggle/', views.toggle_favorite, name='toggle_favorite'),
]