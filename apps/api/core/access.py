from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from core.tenancy import set_tenant


def require_platform(request):
    if not request.user.is_authenticated or not request.user.is_active:
        raise NotAuthenticated()
    if not request.user.is_platform_admin or not request.session.get('mfa_verified'):
        raise PermissionDenied('Privilégio Tavvo e MFA são obrigatórios.')


def authorize_restaurant(request, restaurant_id, action='read'):
    from restaurants.models import Restaurant, RestaurantMembership

    if not request.user.is_authenticated or not request.user.is_active:
        raise NotAuthenticated()
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id)
    membership = RestaurantMembership.objects.filter(
        restaurant=restaurant, user=request.user, status='active',
    ).first()
    platform_read = request.user.is_platform_admin and request.session.get('mfa_verified') and action in ('read', 'audit', 'settings', 'domains', 'domains_read')
    if not membership and not platform_read:
        # Avoid revealing a tenant's existence to an unrelated account.
        from rest_framework.exceptions import NotFound
        raise NotFound()
    if not platform_read:
        if restaurant.status != 'active':
            raise PermissionDenied('Restaurante inativo.')
        if action == 'domains':
            raise PermissionDenied('A gestão de domínios exige privilégio Tavvo.')
        if membership.role != 'manager' and action not in ('read', 'availability'):
            raise PermissionDenied('Esta operação exige um gestor.')
    set_tenant(restaurant.id)
    return restaurant
