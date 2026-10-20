from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, PrivateImageView, ProductImageDeleteView, ProductImageUploadView, ProductViewSet

router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    path("restaurants/<uuid:restaurant_id>/", include(router.urls)),
    path("restaurants/<uuid:restaurant_id>/products/<uuid:product_id>/images/", ProductImageUploadView.as_view(), name="product-image-upload"),
    path("restaurants/<uuid:restaurant_id>/products/<uuid:product_id>/images/<uuid:image_id>/", ProductImageDeleteView.as_view(), name="product-image-delete"),
    path("restaurants/<uuid:restaurant_id>/images/<uuid:image_id>/", PrivateImageView.as_view(), name="private-image"),
]
