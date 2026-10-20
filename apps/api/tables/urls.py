from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import MenuTableViewSet, QRResolverView

router = SimpleRouter()
router.register("tables", MenuTableViewSet, basename="menu-table")

urlpatterns = [
    path("restaurants/<uuid:restaurant_id>/", include(router.urls)),
    path("public/qr/<str:code>/", QRResolverView.as_view(), name="public-qr-resolve"),
]
