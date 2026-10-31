import uuid

from django.db import models
from django.db.models import Q


class OrderSettings(models.Model):
    restaurant = models.OneToOneField('restaurants.Restaurant', primary_key=True, on_delete=models.CASCADE)
    accepting_orders = models.BooleanField(default=False)
    pickup_enabled = models.BooleanField(default=True)
    delivery_enabled = models.BooleanField(default=False)
    table_enabled = models.BooleanField(default=False)
    offline_payment_enabled = models.BooleanField(default=True)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_postal_prefixes = models.JSONField(default=list, blank=True)
    estimated_minutes = models.PositiveIntegerField(default=45)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(delivery_fee__gte=0, minimum_subtotal__gte=0), name='order_settings_nonnegative')]


class Order(models.Model):
    class Status(models.TextChoices):
        AWAITING_PAYMENT = 'awaiting_payment', 'Aguardando pagamento'
        RECEIVED = 'received', 'Recebido'
        ACCEPTED = 'accepted', 'Aceito'
        PREPARING = 'preparing', 'Em preparo'
        READY = 'ready', 'Pronto'
        DISPATCHED = 'dispatched', 'Saiu para entrega'
        COMPLETED = 'completed', 'Concluído'
        CANCELLED = 'cancelled', 'Cancelado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.PROTECT)
    idempotency_key = models.UUIDField()
    request_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.RECEIVED)
    fulfillment = models.CharField(max_length=12, choices=[('pickup', 'Retirada'), ('delivery', 'Entrega'), ('table', 'Mesa')])
    table_label = models.CharField(max_length=80, blank=True)
    customer_name = models.CharField(max_length=120)
    customer_phone = models.CharField(max_length=30)
    customer_email = models.EmailField(blank=True)
    delivery_address = models.JSONField(default=dict, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    currency = models.CharField(max_length=3, default='BRL')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=12, choices=[('offline', 'Na entrega/retirada'), ('stripe', 'Online')])
    payment_status = models.CharField(max_length=24, default='unpaid')
    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)
    checkout_url = models.URLField(max_length=2048, blank=True)
    version = models.PositiveIntegerField(default=1)
    estimated_minutes = models.PositiveIntegerField(default=45)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['restaurant', 'idempotency_key'], name='order_idempotent_per_tenant'),
            models.UniqueConstraint(fields=['restaurant', 'id'], name='order_tenant_id_unique'),
            models.CheckConstraint(condition=Q(subtotal__gte=0, delivery_fee__gte=0, total__gte=0), name='order_amounts_nonnegative'),
        ]
        indexes = [models.Index(fields=['restaurant', 'status', 'created_at'])]


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.PROTECT)
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=Q(quantity__gte=1, quantity__lte=50, unit_price__gte=0, line_total__gte=0), name='order_item_valid_amounts')]


class Subscription(models.Model):
    restaurant = models.OneToOneField('restaurants.Restaurant', primary_key=True, on_delete=models.PROTECT)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    checkout_url = models.URLField(max_length=2048, blank=True)
    status = models.CharField(max_length=32, default='none')
    cancel_at_period_end = models.BooleanField(default=False)
    current_period_end = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class WebhookReceipt(models.Model):
    """Global replay ledger. Never stores customer payloads or private tenant data."""
    event_id = models.CharField(max_length=255, primary_key=True)
    processed_at = models.DateTimeField(auto_now_add=True)


class StripeBinding(models.Model):
    """Trusted routing index for signed webhooks; no contact, amounts or payloads."""
    object_id = models.CharField(max_length=255, primary_key=True)
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.PROTECT)
    order_id = models.UUIDField(null=True)
