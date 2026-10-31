from datetime import datetime, timezone
from urllib.parse import urlparse

import stripe
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from core.tenancy import set_tenant

from .models import Order, StripeBinding, Subscription


class PaymentUnavailable(APIException):
    status_code = 503
    default_detail = 'Pagamento temporariamente indisponível. Tente novamente.'


def client():
    key = settings.STRIPE_SECRET_KEY
    # This release is deliberately sandbox-only; live activation needs Connect onboarding.
    if not key.startswith(('rk_test_', 'sk_test_')):
        raise PaymentUnavailable()
    return stripe.StripeClient(key, stripe_version='2026-10-28.endive', max_network_retries=2,
                               http_client=stripe.RequestsClient(timeout=15))


def origin():
    value = settings.TAVVO_PUBLIC_ORIGIN.rstrip('/')
    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.query:
        raise PaymentUnavailable()
    return value


def safe_call(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except stripe.StripeError as exc:
        # Provider exceptions can contain credentials/customer data: never echo them.
        raise PaymentUnavailable() from exc


def order_checkout(order):
    if order.payment_method != 'stripe' or order.status != 'awaiting_payment' or order.payment_status == 'paid':
        raise ValidationError('Este pedido não está aguardando pagamento online.')
    if order.stripe_session_id:
        session = safe_call(client().v1.checkout.sessions.retrieve, order.stripe_session_id)
        if session.status != 'open':
            raise ValidationError('Este checkout foi encerrado. Consulte o status do pedido.')
        return session.url
    items = [{'quantity': item.quantity, 'price_data': {'currency': 'brl', 'unit_amount': int(item.unit_price * 100),
        'product_data': {'name': item.name}}} for item in order.items.all()]
    if order.delivery_fee:
        items.append({'quantity': 1, 'price_data': {'currency': 'brl', 'unit_amount': int(order.delivery_fee * 100),
            'product_data': {'name': 'Taxa de entrega'}}})
    return_url = f'{origin()}/r/{order.restaurant.slug}?order={order.id}'
    params = {'mode': 'payment', 'line_items': items, 'success_url': return_url, 'cancel_url': return_url,
        'client_reference_id': str(order.id), 'integration_identifier': 'tavvo-orders-xqvmpzrt'}
    if order.customer_email:
        params['customer_email'] = order.customer_email
    session = safe_call(client().v1.checkout.sessions.create, params, options={'idempotency_key': f'tavvo-order-{order.id}'})
    if session.livemode:
        raise PaymentUnavailable()
    order.stripe_session_id, order.checkout_url = session.id, session.url
    order.save(update_fields=['stripe_session_id', 'checkout_url', 'updated_at'])
    StripeBinding.objects.get_or_create(object_id=session.id, defaults={'restaurant': order.restaurant, 'order_id': order.id})
    return session.url


def sync_order_session(order, session_id):
    session = safe_call(client().v1.checkout.sessions.retrieve, session_id)
    if (session.livemode or session.id != order.stripe_session_id or session.mode != 'payment'
            or session.client_reference_id != str(order.id) or session.currency != order.currency.lower()
            or session.amount_total != int(order.total * 100)):
        raise ValidationError('Pagamento não corresponde ao pedido.')
    if session.payment_intent:
        order.stripe_payment_intent = session.payment_intent
        StripeBinding.objects.get_or_create(object_id=session.payment_intent, defaults={'restaurant': order.restaurant, 'order_id': order.id})
    if session.payment_status == 'paid' and order.payment_status not in ('refunded', 'refund_pending', 'disputed', 'review'):
        retry_paid = order.status == 'cancelled' and order.payment_status in ('expired', 'failed')
        order.payment_status = 'paid'
        if order.status == 'awaiting_payment' or retry_paid:
            order.status = 'received'
        sync_charge_state(order)
    elif session.status == 'expired' and order.status == 'awaiting_payment':
        order.status = 'cancelled'
        order.payment_status = 'expired'
    order.version += 1
    order.save()


def sync_charge_state(order):
    """Read current provider state so late checkout events cannot undo refunds."""
    if not order.stripe_payment_intent:
        return
    intent = safe_call(client().v1.payment_intents.retrieve, order.stripe_payment_intent, {'expand': ['latest_charge']})
    charge = intent.to_dict().get('latest_charge')
    if not charge or isinstance(charge, str):
        return
    if charge.get('amount_refunded', 0) >= int(order.total * 100):
        order.payment_status = 'refunded'
        if order.status != 'completed':
            order.status = 'cancelled'
    elif charge.get('amount_refunded', 0) or charge.get('disputed'):
        order.payment_status = 'review'
    elif order.payment_status == 'refund_pending':
        refunds = safe_call(client().v1.refunds.list, {'payment_intent': order.stripe_payment_intent, 'limit': 100})
        if not any(r.status in ('pending', 'requires_action') for r in refunds.data):
            order.payment_status = 'paid'


def refund_order(order):
    if order.payment_method != 'stripe' or order.payment_status != 'paid' or not order.stripe_payment_intent:
        raise ValidationError('Não existe pagamento online confirmado para estornar.')
    refund = safe_call(client().v1.refunds.create, {'payment_intent': order.stripe_payment_intent},
                       options={'idempotency_key': f'tavvo-refund-{order.id}'})
    order.payment_status = 'refunded' if refund.status == 'succeeded' else 'paid' if refund.status in ('failed', 'canceled') else 'refund_pending'
    if refund.status == 'succeeded' and order.status != 'completed':
        order.status = 'cancelled'
    order.version += 1
    order.save()


@transaction.atomic
def subscription_checkout(restaurant, user):
    if not settings.STRIPE_SUBSCRIPTION_PRICE_ID or not settings.STRIPE_WEBHOOK_SECRET:
        raise PaymentUnavailable()
    Subscription.objects.get_or_create(restaurant=restaurant)
    sub = Subscription.objects.select_for_update().get(restaurant=restaurant)
    if sub.stripe_subscription_id:
        sync_subscription(sub, sub.stripe_subscription_id)
        if sub.status not in ('canceled', 'incomplete_expired'):
            raise ValidationError('Já existe uma assinatura. Use Gerenciar assinatura.')
    if not sub.stripe_customer_id:
        customer = safe_call(client().v1.customers.create, {'email': user.email, 'name': restaurant.name},
            options={'idempotency_key': f'tavvo-customer-{restaurant.id}'})
        sub.stripe_customer_id = customer.id
        sub.save()
        StripeBinding.objects.get_or_create(object_id=customer.id, defaults={'restaurant': restaurant})
    if sub.stripe_session_id:
        old = safe_call(client().v1.checkout.sessions.retrieve, sub.stripe_session_id)
        if old.status == 'open':
            return old.url
        if old.status == 'complete' and old.subscription:
            sync_subscription(sub, old.subscription)
            if sub.status not in ('canceled', 'incomplete_expired'):
                raise ValidationError('Assinatura já criada. Atualize o painel.')
    session = safe_call(client().v1.checkout.sessions.create, {'mode': 'subscription', 'customer': sub.stripe_customer_id,
        'line_items': [{'price': settings.STRIPE_SUBSCRIPTION_PRICE_ID, 'quantity': 1}],
        'success_url': settings.TAVVO_ADMIN_ORIGIN, 'cancel_url': settings.TAVVO_ADMIN_ORIGIN,
        'integration_identifier': 'tavvo-billing-kzprqvnt'},
        options={'idempotency_key': f'tavvo-sub-{restaurant.id}-{sub.stripe_session_id or "first"}'})
    sub.stripe_session_id, sub.checkout_url = session.id, session.url
    sub.save()
    StripeBinding.objects.get_or_create(object_id=session.id, defaults={'restaurant': restaurant})
    return session.url


def sync_subscription(sub, subscription_id):
    current = safe_call(client().v1.subscriptions.retrieve, subscription_id)
    if current.livemode or current.customer != sub.stripe_customer_id:
        raise ValidationError('Assinatura não corresponde ao restaurante.')
    sub.stripe_subscription_id = current.id
    sub.status = current.status
    sub.cancel_at_period_end = bool(current.cancel_at_period_end or current.to_dict().get('cancel_at'))
    periods = [x.get('current_period_end') for x in current.to_dict()['items']['data'] if x.get('current_period_end')]
    sub.current_period_end = datetime.fromtimestamp(max(periods), timezone.utc) if periods else None
    sub.save()
    StripeBinding.objects.get_or_create(object_id=current.id, defaults={'restaurant': sub.restaurant})


def subscription_portal(restaurant):
    sub = Subscription.objects.filter(restaurant=restaurant).first()
    if not sub or not sub.stripe_customer_id:
        raise ValidationError('Contrate a assinatura de teste antes de abrir o portal.')
    return safe_call(client().v1.billing_portal.sessions.create,
        {'customer': sub.stripe_customer_id, 'return_url': settings.TAVVO_ADMIN_ORIGIN,
         **({'configuration': settings.STRIPE_PORTAL_CONFIGURATION_ID} if settings.STRIPE_PORTAL_CONFIGURATION_ID else {})}).url


def process_event(event):
    """Map signed provider object IDs through our own index, then enter tenant RLS."""
    obj, kind = event['data']['object'], event['type']
    intent_id = obj.get('payment_intent')
    binding = StripeBinding.objects.filter(object_id=obj['id']).first()
    if not binding and obj.get('payment_intent'):
        binding = StripeBinding.objects.filter(object_id=obj['payment_intent']).first()
    if not binding and obj.get('charge') and kind.startswith(('refund.', 'charge.dispute.', 'radar.')):
        charge = safe_call(client().v1.charges.retrieve, obj['charge'])
        intent_id = charge.payment_intent
        binding = StripeBinding.objects.filter(object_id=charge.payment_intent).first()
        if not binding and charge.customer:
            binding = StripeBinding.objects.filter(object_id=charge.customer).first()
    # Refund/dispute may arrive before checkout.completed has bound its intent.
    if not binding and intent_id:
        sessions = safe_call(client().v1.checkout.sessions.list, {'payment_intent': intent_id, 'limit': 1})
        if sessions.data:
            binding = StripeBinding.objects.filter(object_id=sessions.data[0].id).first()
    if not binding and obj.get('customer'):
        binding = StripeBinding.objects.filter(object_id=obj['customer']).first()
    if not binding:
        return
    set_tenant(binding.restaurant_id)
    if binding.order_id:
        order = Order.objects.select_for_update().get(pk=binding.order_id, restaurant_id=binding.restaurant_id)
        if not order.stripe_payment_intent and not kind.startswith('checkout.session.'):
            sync_order_session(order, order.stripe_session_id)
        if kind.startswith('checkout.session.'):
            sync_order_session(order, obj['id'])
            if kind == 'checkout.session.async_payment_failed' and order.payment_status == 'unpaid':
                order.payment_status, order.status = 'failed', 'cancelled'
                order.save(update_fields=['payment_status', 'status', 'updated_at'])
        elif kind.startswith('refund.') or kind == 'charge.refunded':
            sync_charge_state(order)
            order.version += 1
            order.save()
        elif kind.startswith(('charge.dispute.', 'radar.early_fraud_warning.')):
            order.payment_status = 'review'
            order.version += 1
            order.save()
    else:
        sub = Subscription.objects.select_for_update().get(restaurant_id=binding.restaurant_id)
        subscription_id = obj['id'] if kind.startswith('customer.subscription.') else obj.get('subscription')
        if kind.startswith('invoice.'):
            subscription_id = ((obj.get('parent') or {}).get('subscription_details') or {}).get('subscription') or obj.get('subscription')
        if subscription_id:
            # An event from a previous canceled subscription must not replace a newer one.
            if sub.stripe_subscription_id and subscription_id != sub.stripe_subscription_id:
                latest = safe_call(client().v1.checkout.sessions.retrieve, sub.stripe_session_id)
                if latest.subscription != subscription_id:
                    return
            sync_subscription(sub, subscription_id)
        if kind.startswith(('refund.', 'charge.dispute.', 'radar.early_fraud_warning.')) or kind == 'charge.refunded':
            sub.status = 'review'
            sub.save()
