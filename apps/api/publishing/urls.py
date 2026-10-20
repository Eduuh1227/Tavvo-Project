from django.urls import path

from .views import DomainResolverView, PublicImageView, PublicMenuView, PublicRestaurantView

urlpatterns = [
    path("public/resolve/", DomainResolverView.as_view(), name="public-domain-resolve"),
    path("public/restaurants/<slug:slug>/", PublicRestaurantView.as_view(), name="public-restaurant"),
    path("public/restaurants/<slug:slug>/menu/", PublicMenuView.as_view(), name="public-menu"),
    path("public/restaurants/<slug:slug>/images/<uuid:image_id>/", PublicImageView.as_view(), name="public-image"),
]
