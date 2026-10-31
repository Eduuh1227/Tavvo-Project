from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core.views import health, ready

urlpatterns = [
    path('health/', health), path('ready/', ready),
    path('v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('v1/', include('identity.urls')),
    path('v1/', include('restaurants.urls')),
    path('v1/', include('catalog.urls')),
    path('v1/', include('publishing.urls')),
    path('v1/', include('tables.urls')),
    path('v1/', include('audit.urls')),
    path('v1/', include('commerce.urls')),
]
