from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import DomainViewSet, MembershipViewSet, PlatformRestaurantViewSet, SettingsView

platform_router = SimpleRouter()
platform_router.register("restaurants", PlatformRestaurantViewSet, basename="platform-restaurant")
membership_router = SimpleRouter()
membership_router.register("memberships", MembershipViewSet, basename="membership")
tenant_router = SimpleRouter()
tenant_router.register("domains", DomainViewSet, basename="domain")

urlpatterns = [
    path("platform/", include(platform_router.urls)),
    path("platform/restaurants/<uuid:restaurant_id>/", include(membership_router.urls)),
    path("restaurants/<uuid:restaurant_id>/settings/", SettingsView.as_view(), name="restaurant-settings"),
    path("restaurants/<uuid:restaurant_id>/", include(tenant_router.urls)),
]
