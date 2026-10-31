import re

from django.conf import settings
from rest_framework import serializers

from .models import Order, OrderItem, OrderSettings, Subscription


class OrderSettingsSerializer(serializers.ModelSerializer):
    online_payment_available = serializers.SerializerMethodField()
    test_mode = serializers.SerializerMethodField()

    class Meta:
        model = OrderSettings
        exclude = ['restaurant']

    def get_online_payment_available(self, obj) -> bool:
        return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)

    def get_test_mode(self, obj) -> bool:
        return True

    def validate(self, attrs):
        for field in ('delivery_fee', 'minimum_subtotal'):
            if attrs.get(field, 0) < 0:
                raise serializers.ValidationError({field: 'O valor não pode ser negativo.'})
        prefixes = attrs.get('delivery_postal_prefixes', getattr(self.instance, 'delivery_postal_prefixes', []))
        if not isinstance(prefixes, list) or len(prefixes) > 100 or any(not isinstance(x, str) or not re.fullmatch(r'\d{2,8}', x) for x in prefixes):
            raise serializers.ValidationError({'delivery_postal_prefixes': 'Informe até 100 prefixos de CEP com 2 a 8 dígitos.'})
        delivery = attrs.get('delivery_enabled', getattr(self.instance, 'delivery_enabled', False))
        if delivery and not prefixes:
            raise serializers.ValidationError({'delivery_postal_prefixes': 'Defina a área de entrega por prefixos de CEP.'})
        if 'estimated_minutes' in attrs and not 5 <= attrs['estimated_minutes'] <= 240:
            raise serializers.ValidationError({'estimated_minutes': 'Use de 5 a 240 minutos.'})
        return attrs


class OrderLineInput(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=50)


class AddressInput(serializers.Serializer):
    street = serializers.CharField(max_length=160)
    number = serializers.CharField(max_length=20)
    neighborhood = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    postal_code = serializers.RegexField(r'^\d{8}$')
    complement = serializers.CharField(max_length=160, required=False, allow_blank=True)


class CreateOrderInput(serializers.Serializer):
    idempotency_key = serializers.UUIDField()
    items = OrderLineInput(many=True, min_length=1, max_length=30)
    customer_name = serializers.CharField(max_length=120)
    customer_phone = serializers.RegexField(r'^\+?[0-9 ()-]{8,30}$')
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    fulfillment = serializers.ChoiceField(choices=['pickup', 'delivery', 'table'])
    delivery_address = AddressInput(required=False)
    table_code = serializers.CharField(max_length=90, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=['offline', 'stripe'])


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'name', 'quantity', 'unit_price', 'line_total']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'fulfillment', 'table_label', 'customer_name', 'customer_phone', 'customer_email',
                  'delivery_address', 'notes', 'currency', 'subtotal', 'delivery_fee', 'total', 'payment_method',
                  'payment_status', 'version', 'estimated_minutes', 'created_at', 'updated_at', 'items']
        read_only_fields = fields


class PublicOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'fulfillment', 'table_label', 'currency', 'subtotal', 'delivery_fee', 'total',
                  'payment_method', 'payment_status', 'estimated_minutes', 'created_at', 'items']


class OrderCreatedSerializer(serializers.Serializer):
    order = PublicOrderSerializer()
    access_token = serializers.CharField()


class TransitionInput(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
    version = serializers.IntegerField(min_value=1)


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['status', 'cancel_at_period_end', 'current_period_end', 'updated_at']


class CheckoutResult(serializers.Serializer):
    url = serializers.URLField()


class BillingStatusSerializer(serializers.Serializer):
    subscription = SubscriptionSerializer()
    available = serializers.BooleanField()
    test_mode = serializers.BooleanField()
    plan_label = serializers.CharField()
