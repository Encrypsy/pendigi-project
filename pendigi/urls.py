from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/articles/', permanent=False), name='home'),
    path('accounts/', include('accounts.urls')),
    path('articles/', include('articles.urls')),
    path('interactions/', include('interactions.urls')),
    path('reading-journal/', include('reading_journal.urls')),
    path('fiksi/', include('fiction.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)