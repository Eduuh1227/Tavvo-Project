from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound

from core.tenancy import set_tenant
from restaurants.models import Restaurant, RestaurantDomain
from restaurants.serializers import normalize_hostname


def resolve_domain(hostname):
    hostname = normalize_hostname(hostname)
    domain = get_object_or_404(
        RestaurantDomain.objects.select_related("restaurant"), hostname=hostname,
        status=RestaurantDomain.Status.VERIFIED, restaurant__status=Restaurant.Status.ACTIVE,
    )
    set_tenant(domain.restaurant_id)
    return domain.restaurant


def public_restaurant(slug, request=None):
    restaurant = get_object_or_404(Restaurant, slug=slug, status=Restaurant.Status.ACTIVE)
    # A supplied domain must match this restaurant; absence uses the explicit public slug route.
    if request is not None and "hostname" in request.query_params:
        domain_restaurant = resolve_domain(request.query_params["hostname"])
        if domain_restaurant.pk != restaurant.pk:
            raise NotFound()
    set_tenant(restaurant.pk)
    return restaurant
