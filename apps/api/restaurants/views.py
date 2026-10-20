from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from audit.services import record
from core.access import authorize_restaurant, require_platform
from core.tenancy import set_tenant

from .models import Restaurant, RestaurantDomain, RestaurantMembership, RestaurantSettings
from .serializers import DomainSerializer, MembershipSerializer, RestaurantSerializer, SettingsSerializer


class TenantAccessMixin:
    permission_classes = [IsAuthenticated]

    def restaurant(self, action=None):
        requested_action = action or ("read" if self.request.method in ("GET", "HEAD", "OPTIONS") else "manage")
        return authorize_restaurant(self.request, self.kwargs["restaurant_id"], requested_action)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["restaurant"] = self.restaurant()
        return context


class PlatformRestaurantViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                                mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RestaurantSerializer
    queryset = Restaurant.objects.all()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_platform(request)

    def perform_create(self, serializer):
        restaurant = serializer.save()
        set_tenant(restaurant.pk)
        RestaurantSettings.objects.create(restaurant=restaurant)
        record(self.request, restaurant, "restaurant.created", restaurant)

    def perform_update(self, serializer):
        restaurant = serializer.save()
        set_tenant(restaurant.pk)
        record(self.request, restaurant, "restaurant.updated", restaurant, {"status": restaurant.status})


class MembershipViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                        mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MembershipSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_platform(request)
        self.restaurant_object = get_object_or_404(Restaurant, pk=kwargs["restaurant_id"])
        set_tenant(self.restaurant_object.pk)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RestaurantMembership.objects.none()
        return RestaurantMembership.objects.filter(restaurant=self.restaurant_object).select_related("user")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["restaurant"] = self.restaurant_object
        return context

    def perform_create(self, serializer):
        membership = serializer.save(restaurant=self.restaurant_object)
        record(self.request, self.restaurant_object, "membership.created", membership, {"role": membership.role, "status": membership.status})

    def perform_update(self, serializer):
        membership = serializer.save()
        record(self.request, self.restaurant_object, "membership.updated", membership, {"role": membership.role, "status": membership.status})


class SettingsView(TenantAccessMixin, generics.RetrieveUpdateAPIView):
    serializer_class = SettingsSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def restaurant(self, action=None):
        return super().restaurant("settings")

    def get_object(self):
        restaurant = self.restaurant()
        instance, _ = RestaurantSettings.objects.get_or_create(restaurant=restaurant)
        return instance

    def perform_update(self, serializer):
        settings = serializer.save()
        record(self.request, self.restaurant("manage"), "settings.updated", settings)


class DomainViewSet(TenantAccessMixin, viewsets.ModelViewSet):
    serializer_class = DomainSerializer

    def restaurant(self, action=None):
        return super().restaurant("domains_read" if self.request.method in ("GET", "HEAD", "OPTIONS") else "domains")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RestaurantDomain.objects.none()
        return RestaurantDomain.objects.filter(restaurant=self.restaurant())

    def perform_create(self, serializer):
        restaurant = self.restaurant("manage")
        domain = serializer.save(restaurant=restaurant)
        record(self.request, restaurant, "domain.created", domain)

    def perform_update(self, serializer):
        domain = serializer.save()
        record(self.request, self.restaurant("manage"), "domain.updated", domain, {"status": domain.status})

    def perform_destroy(self, instance):
        record(self.request, self.restaurant("manage"), "domain.deleted", instance)
        instance.delete()
