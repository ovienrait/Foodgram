from api.views import ShortLinkRedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('api/', include('api.urls')),
    path('s/<str:short_hash>/', ShortLinkRedirectView.as_view(),
         name='shortlink'),
    path('admin/', admin.site.urls)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
