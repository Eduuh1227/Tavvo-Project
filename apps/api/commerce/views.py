from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record
from core.access import authorize_restaurant
from identity.security import consume_limit
from publishing.services import public_restaurant
from publishing.views import PublicView
from restaurants.views import TenantAccessMixin

from .models import Order, OrderSettings, Subscription
from .serializers import (BillingStatusSerializer, CheckoutResult, CreateOrderInput, OrderCreatedSerializer,
                          OrderSerializer, OrderSettingsSerializer, PublicOrderSerializer, TransitionInput)
from .services import access_token, authorize_order, create_order, transition


class PublicOrderSettingsView(PublicView):
    @extend_schema(responses=OrderSettingsSerializer)
    def get(self, request, slug):
        restaurant = public_restaurant(slug, request)
        policy = OrderSettings.objects.filter(restaurant=restaurant).first() or OrderSettings(restaurant=restaurant)
        return Response(OrderSettingsSerializer(policy).data)


class OrderSettingsView(APIView):
    @extend_schema(responses=OrderSettingsSerializer)
    def get(self, request, restaurant_id):
        restaurant = authorize_restaurant(request, restaurant_id, 'settings')
        policy, _ = OrderSettings.objects.get_or_create(restaurant=restaurant)
        return Response(OrderSettingsSerializer(policy).data)

    @extend_schema(request=OrderSettingsSerializer, responses=OrderSettingsSerializer)
    def patch(self, request, restaurant_id):
        restaurant = authorize_restaurant(request, restaurant_id, 'manage')
        policy, _ = OrderSettings.objects.get_or_create(restaurant=restaurant)
        values = OrderSettingsSerializer(policy, data=request.data, partial=True)
        values.is_valid(raise_exception=True)
        values.save()
        record(request, restaurant, 'order_settings.updated', policy)
        return Response(values.data)


class PublicOrderCreateView(PublicView):
    @extend_schema(request=CreateOrderInput, responses={201: OrderCreatedSerializer, 200: OrderCreatedSerializer})
    def post(self, request, slug):
        if not consume_limit('order-create', request.META.get('REMOTE_ADDR', 'unknown'), 30, 300):
            return Response({'detail': 'Aguarde antes de tentar novamente.'}, status=429)
        restaurant = public_restaurant(slug, request)
        values = CreateOrderInput(data=request.data)
        values.is_valid(raise_exception=True)
        order, created = create_order(restaurant, values.validated_data, request)
        return Response({'order': PublicOrderSerializer(order).data, 'access_token': access_token(order)}, status=201 if created else 200)


class PublicOrderDetailView(PublicView):
    @extend_schema(responses=PublicOrderSerializer)
    def get(self, request, slug, order_id):
        restaurant = public_restaurant(slug, request)
        order = get_object_or_404(Order, restaurant=restaurant, pk=order_id)
        authorize_order(order, request)
        return Response(PublicOrderSerializer(order).data)


class PublicCheckoutView(PublicView):
    @extend_schema(request=None, responses=CheckoutResult)
    def post(self, request, slug, order_id):
        from .payments import order_checkout
        restaurant = public_restaurant(slug, request)
        order = get_object_or_404(Order.objects.select_for_update(), restaurant=restaurant, pk=order_id)
        authorize_order(order, request)
        return Response({'url': order_checkout(order)})


class OrderViewSet(TenantAccessMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        return Order.objects.filter(restaurant=self.restaurant('orders')).prefetch_related('items')

    @extend_schema(request=TransitionInput, responses=OrderSerializer)
    @action(detail=True, methods=['post'], url_path='transition')
    def change_status(self, request, **kwargs):
        values = TransitionInput(data=request.data)
        values.is_valid(raise_exception=True)
        with transaction.atomic():
            order = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs['pk'])
            transition(order, values.validated_data['status'], values.validated_data['version'], request)
        return Response(OrderSerializer(order).data)

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=['post'], url_path='received-payment')
    def received_payment(self, request, **kwargs):
        order = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs['pk'])
        if order.payment_method != 'offline' or order.status in ('cancelled', 'awaiting_payment'):
            raise ValidationError('Este pagamento não pode ser confirmado manualmente.')
        if order.payment_status != 'paid':
            order.payment_status = 'paid'
            order.version += 1
            order.save(update_fields=['payment_status', 'version', 'updated_at'])
            record(request, order.restaurant, 'order.offline_payment_received', order)
        return Response(OrderSerializer(order).data)

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=['post'])
    def refund(self, request, **kwargs):
        from .payments import refund_order
        authorize_restaurant(request, kwargs['restaurant_id'], 'manage')
        order = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs['pk'])
        refund_order(order)
        record(request, order.restaurant, 'order.refund_requested', order)
        return Response(OrderSerializer(order).data)


class BillingView(APIView):
    @extend_schema(responses=BillingStatusSerializer)
    def get(self, request, restaurant_id):
        restaurant = authorize_restaurant(request, restaurant_id, 'settings')
        sub, _ = Subscription.objects.get_or_create(restaurant=restaurant)
        return Response(BillingStatusSerializer({'subscription': sub, 'available': bool(settings.STRIPE_SUBSCRIPTION_PRICE_ID and settings.STRIPE_WEBHOOK_SECRET),
            'test_mode': True, 'plan_label': settings.STRIPE_PLAN_LABEL}).data)


class BillingCheckoutView(APIView):
    @extend_schema(request=None, responses=CheckoutResult)
    def post(self, request, restaurant_id):
        from .payments import subscription_checkout
        restaurant = authorize_restaurant(request, restaurant_id, 'manage')
        return Response({'url': subscription_checkout(restaurant, request.user)})


class BillingPortalView(APIView):
    @extend_schema(request=None, responses=CheckoutResult)
    def post(self, request, restaurant_id):
        from .payments import subscription_portal
        restaurant = authorize_restaurant(request, restaurant_id, 'manage')
        return Response({'url': subscription_portal(restaurant)})
