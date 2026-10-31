import hashlib
import json
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.exceptions import NotFound, ValidationError

from audit.services import record
from catalog.models import Product
from tables.models import MenuTable

from .models import Order, OrderItem, OrderSettings


def access_token(order):
    return salted_hmac('tavvo.order.access', f'{order.restaurant_id}:{order.id}:{order.idempotency_key}', algorithm='sha256').hexdigest()


def authorize_order(order, request):
    if not constant_time_compare(access_token(order), request.headers.get('X-Order-Token', '')[:128]):
        raise NotFound()


@transaction.atomic
def create_order(restaurant, values, request):
    # One short lock per restaurant serializes idempotency and settings changes.
    OrderSettings.objects.get_or_create(restaurant=restaurant)
    policy = OrderSettings.objects.select_for_update().get(restaurant=restaurant)
    digest = hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()
    existing = Order.objects.filter(restaurant=restaurant, idempotency_key=values['idempotency_key']).first()
    if existing:
        if not constant_time_compare(existing.request_hash, digest):
            raise ValidationError('Esta chave já foi usada para outro pedido.')
        return existing, False
    if not policy.accepting_orders:
        raise ValidationError('O restaurante não está recebendo pedidos agora.')
    mode = values['fulfillment']
    if not getattr(policy, f'{mode}_enabled'):
        raise ValidationError('Esta modalidade não está disponível.')
    if values['payment_method'] == 'offline' and not policy.offline_payment_enabled:
        raise ValidationError('Pagamento na entrega/retirada não está disponível.')
    if values['payment_method'] == 'stripe' and not (settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET):
        raise ValidationError('Pagamento online indisponível.')
    address = values.get('delivery_address', {})
    if mode == 'delivery':
        if not address or not policy.delivery_postal_prefixes or not any(address['postal_code'].startswith(p) for p in policy.delivery_postal_prefixes):
            raise ValidationError({'delivery_address': 'CEP fora da área de entrega.'})
    elif address:
        raise ValidationError('Endereço só é necessário para entrega.')
    label = ''
    if mode == 'table':
        table = MenuTable.objects.filter(restaurant=restaurant, public_code=values.get('table_code', ''), status='active').first()
        if not table:
            raise ValidationError('Escaneie um QR Code de mesa ativo deste restaurante.')
        label = table.label
    identifiers = [line['product_id'] for line in values['items']]
    if len(set(identifiers)) != len(identifiers):
        raise ValidationError('Agrupe as quantidades de cada produto em uma única linha.')
    products = {p.pk: p for p in Product.objects.select_for_update().filter(
        restaurant=restaurant, pk__in=identifiers, archived_at__isnull=True,
        is_published=True, is_available=True, category__restaurant=restaurant,
        category__archived_at__isnull=True, category__is_published=True)}
    if len(products) != len(identifiers):
        raise ValidationError('Um ou mais produtos não estão disponíveis. Atualize o cardápio.')
    if any(p.currency != 'BRL' for p in products.values()):
        raise ValidationError('Os pedidos desta etapa aceitam produtos em BRL.')
    subtotal = sum((products[x['product_id']].price * x['quantity'] for x in values['items']), Decimal('0.00'))
    fee = policy.delivery_fee if mode == 'delivery' else Decimal('0.00')
    if subtotal < policy.minimum_subtotal or subtotal + fee > Decimal('999999.99') or subtotal + fee <= 0:
        raise ValidationError('O total não atende aos limites do restaurante.')
    online = values['payment_method'] == 'stripe'
    order = Order.objects.create(restaurant=restaurant, idempotency_key=values['idempotency_key'], request_hash=digest,
        status='awaiting_payment' if online else 'received', fulfillment=mode, table_label=label,
        customer_name=values['customer_name'], customer_phone=values['customer_phone'], customer_email=values.get('customer_email', ''),
        delivery_address=address, notes=values.get('notes', ''), subtotal=subtotal, delivery_fee=fee, total=subtotal+fee,
        payment_method=values['payment_method'], estimated_minutes=policy.estimated_minutes)
    OrderItem.objects.bulk_create([OrderItem(restaurant=restaurant, order=order, product=products[x['product_id']],
        name=products[x['product_id']].name, quantity=x['quantity'], unit_price=products[x['product_id']].price,
        line_total=products[x['product_id']].price*x['quantity']) for x in values['items']])
    record(request, restaurant, 'order.created', order, {'fulfillment': mode, 'payment_method': order.payment_method})
    return order, True


TRANSITIONS = {
    'awaiting_payment': set(),
    'received': {'accepted', 'cancelled'},
    'accepted': {'preparing', 'cancelled'},
    'preparing': {'ready', 'cancelled'},
    'ready': {'dispatched', 'completed', 'cancelled'},
    'dispatched': {'completed'},
    'completed': set(), 'cancelled': set(),
}


def transition(order, target, version, request):
    if order.version != version:
        raise ValidationError('O pedido mudou. Atualize antes de continuar.')
    if target not in TRANSITIONS[order.status]:
        raise ValidationError('Transição de status inválida.')
    if target == 'dispatched' and order.fulfillment != 'delivery':
        raise ValidationError('Apenas pedidos de entrega podem ser despachados.')
    if target == 'completed' and order.fulfillment == 'delivery' and order.status != 'dispatched':
        raise ValidationError('Registre a saída para entrega antes da conclusão.')
    if target == 'cancelled' and order.payment_method == 'stripe' and order.payment_status == 'paid':
        raise ValidationError('Estorne o pagamento antes de cancelar o pedido.')
    if target in ('accepted', 'preparing', 'ready', 'dispatched', 'completed') and order.payment_method == 'stripe' and order.payment_status != 'paid':
        raise ValidationError('Aguarde a confirmação do pagamento.')
    if target == 'completed' and order.payment_status != 'paid':
        raise ValidationError('Confirme o recebimento do pagamento antes de concluir.')
    order.status = target
    order.version += 1
    order.save(update_fields=['status', 'version', 'updated_at'])
    record(request, order.restaurant, 'order.status_changed', order, {'status': target})
