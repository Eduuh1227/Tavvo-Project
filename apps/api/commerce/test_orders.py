import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import patch

import pytest
import stripe
from django.db import connection, transaction, IntegrityError
from rest_framework.test import APIClient

from catalog.tests.test_catalog_flows import tenants, authenticated
from core.tenancy import set_tenant
from .models import Order, OrderItem, OrderSettings, StripeBinding, WebhookReceipt

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(tenants):
    set_tenant(tenants['a'].id)
    OrderSettings.objects.create(restaurant=tenants['a'], accepting_orders=True, delivery_enabled=True,
        delivery_postal_prefixes=['01'], delivery_fee='5.00')
    return tenants, APIClient(), '/v1/public/restaurants/restaurante-a/orders/'


def payload(t, **extra):
    return dict(idempotency_key=str(uuid.uuid4()), items=[{'product_id': str(t['product_a'].id), 'quantity': 2}],
        customer_name='Cliente Teste', customer_phone='11999999999', fulfillment='pickup', payment_method='offline', **extra)


def test_price_idempotency_and_private_tracking(setup):
    t, client, url = setup
    data = payload(t, total='0.01')
    first = client.post(url, data, format='json')
    assert first.status_code == 201, first.data
    assert first.data['order']['total'] == '25.00'
    assert 'customer_phone' not in first.data['order']
    again = client.post(url, data, format='json')
    assert again.status_code == 200 and again.data == first.data
    data['items'][0]['quantity'] = 3
    assert client.post(url, data, format='json').status_code == 400
    detail = url + first.data['order']['id'] + '/'
    assert client.get(detail).status_code == 404
    assert client.get(detail, HTTP_X_ORDER_TOKEN=first.data['access_token']).status_code == 200
    assert client.get(detail.replace('restaurante-a', 'restaurante-b'), HTTP_X_ORDER_TOKEN=first.data['access_token']).status_code == 404


def test_delivery_coverage_and_foreign_product(setup):
    t, client, url = setup
    data = payload(t)
    data['items'][0]['product_id'] = str(t['product_b'].id)
    assert client.post(url, data, format='json').status_code == 400
    data = payload(t)
    data.update(fulfillment='delivery', delivery_address={'street':'Rua Teste','number':'1','neighborhood':'Centro','city':'São Paulo','postal_code':'99999999'})
    assert client.post(url, data, format='json').status_code == 400
    data['delivery_address']['postal_code'] = '01001000'
    result = client.post(url, data, format='json')
    assert result.status_code == 201 and result.data['order']['total'] == '30.00'
    t['product_a'].is_available = False
    t['product_a'].save()
    assert client.post(url, payload(t), format='json').status_code == 400


def test_permissions_versions_and_fulfillment(setup):
    t, public, url = setup
    result = public.post(url, payload(t), format='json')
    oid = result.data['order']['id']
    path = f'/v1/restaurants/{t["a"].id}/orders/{oid}/'
    staff = authenticated(t['staff'])
    assert authenticated(t['manager_b']).get(path).status_code == 404
    assert staff.post(path+'refund/').status_code == 403
    assert staff.patch(f'/v1/restaurants/{t["a"].id}/ordering/', {'accepting_orders':False}, format='json').status_code == 403
    for version, status in enumerate(['accepted','preparing','ready'], start=1):
        changed = staff.post(path+'transition/', {'status':status,'version':version}, format='json')
        assert changed.status_code == 200, changed.data
    assert staff.post(path+'transition/', {'status':'completed','version':4}, format='json').status_code == 400
    paid = staff.post(path+'received-payment/')
    assert paid.status_code == 200
    assert staff.post(path+'transition/', {'status':'completed','version':4}, format='json').status_code == 400
    assert staff.post(path+'transition/', {'status':'completed','version':5}, format='json').status_code == 200


def test_order_rls_and_composite_fk(setup):
    t, public, url = setup
    oid = public.post(url, payload(t), format='json').data['order']['id']
    with pytest.raises(IntegrityError), transaction.atomic():
        OrderItem.objects.create(restaurant=t['a'], order_id=oid, product=t['product_b'], name='Invalid', quantity=1, unit_price=1, line_total=1)
    with connection.cursor() as cursor:
        cursor.execute('SET LOCAL ROLE tavvo_app')
    set_tenant(t['b'].id)
    assert not Order.objects.exists() and not OrderItem.objects.exists()
    set_tenant(t['a'].id)
    assert Order.objects.count() == 1 and OrderItem.objects.count() == 1


def signed(client, event, secret='whsec_test'):
    body = json.dumps(event)
    stamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), f'{stamp}.{body}'.encode(), hashlib.sha256).hexdigest()
    return client.post('/v1/payments/stripe/webhook/', body, content_type='application/json', HTTP_STRIPE_SIGNATURE=f't={stamp},v1={signature}')


def test_webhook_signature_replay_async_and_refund_ordering(setup, settings):
    settings.STRIPE_SECRET_KEY='sk_test_fixture'
    settings.STRIPE_WEBHOOK_SECRET='whsec_test'
    t, public, url = setup
    data = payload(t); data['payment_method'] = 'stripe'
    oid = public.post(url, data, format='json').data['order']['id']
    order = Order.objects.get(pk=oid)
    order.stripe_session_id='cs_test_order'; order.save()
    StripeBinding.objects.create(object_id=order.stripe_session_id, restaurant=t['a'], order_id=oid)
    event={'id':'evt_test_one','type':'checkout.session.completed','livemode':False,'data':{'object':{'id':order.stripe_session_id}}}
    assert public.post('/v1/payments/stripe/webhook/', event, format='json').status_code == 400
    session = stripe.StripeObject.construct_from(dict(id=order.stripe_session_id,livemode=False,mode='payment',client_reference_id=oid,
        currency='brl',amount_total=2500,payment_intent='pi_test_order',payment_status='unpaid',status='complete'), None)
    with patch('commerce.payments.client') as factory:
        api=factory.return_value.v1
        api.checkout.sessions.retrieve.return_value=session
        api.payment_intents.retrieve.return_value=stripe.StripeObject.construct_from({'latest_charge': {'amount_refunded':0,'disputed':False}}, None)
        assert signed(public, event).status_code == 200
        order.refresh_from_db(); assert order.status == 'awaiting_payment'
        assert signed(public, event).status_code == 200
        assert api.checkout.sessions.retrieve.call_count == 1
        session.payment_status='paid'; event['id']='evt_test_paid'; event['type']='checkout.session.async_payment_succeeded'
        assert signed(public, event).status_code == 200
        order.refresh_from_db(); assert order.status == 'received' and order.payment_status == 'paid'
        api.payment_intents.retrieve.return_value=stripe.StripeObject.construct_from({'latest_charge': {'amount_refunded':2500,'disputed':False}}, None)
        event['id']='evt_test_late_checkout'
        assert signed(public, event).status_code == 200
        order.refresh_from_db(); assert order.payment_status == 'refunded' and order.status == 'cancelled'
        event['id']='evt_test_bad_amount';session.amount_total=1
        assert signed(public,event).status_code == 400
        assert not WebhookReceipt.objects.filter(pk=event['id']).exists()


def test_subscription_webhook_reads_latest_state_and_rejects_old_subscription(setup, settings):
    from .models import Subscription
    settings.STRIPE_WEBHOOK_SECRET='whsec_test'
    t, public, _ = setup
    sub=Subscription.objects.create(restaurant=t['a'], stripe_customer_id='cus_test',stripe_session_id='cs_sub',stripe_subscription_id='sub_new')
    StripeBinding.objects.create(object_id='cus_test',restaurant=t['a'])
    event={'id':'evt_sub','type':'invoice.payment_failed','livemode':False,'data':{'object':{'id':'in_test','customer':'cus_test','parent':{'subscription_details':{'subscription':'sub_new'}}}}}
    with patch('commerce.payments.client') as factory:
        api=factory.return_value.v1
        current=stripe.StripeObject.construct_from({'id':'sub_new','customer':'cus_test','livemode':False,'status':'past_due','cancel_at_period_end':False,'items':{'data':[{'current_period_end':1800000000}]}},None)
        api.subscriptions.retrieve.return_value=current
        assert signed(public,event).status_code==200
        sub.refresh_from_db();assert sub.status=='past_due' and sub.current_period_end
        event.update(id='evt_old_sub',type='customer.subscription.deleted')
        event['data']['object']={'id':'sub_old','customer':'cus_test'}
        api.checkout.sessions.retrieve.return_value=stripe.StripeObject.construct_from({'subscription':'sub_new'},None)
        assert signed(public,event).status_code==200
        sub.refresh_from_db();assert sub.stripe_subscription_id=='sub_new' and sub.status=='past_due'
