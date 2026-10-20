from decimal import Decimal

import pytest
from django.db import connection, transaction, IntegrityError, DatabaseError

from catalog.models import Category, Product
from core.tenancy import set_tenant
from restaurants.models import Restaurant

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenants():
    first = Restaurant.objects.create(name='Restaurant A', slug='rls-a')
    second = Restaurant.objects.create(name='Restaurant B', slug='rls-b')
    category_a = Category.objects.create(restaurant=first, name='Category A')
    category_b = Category.objects.create(restaurant=second, name='Category B')
    product_a = Product.objects.create(restaurant=first, category=category_a, name='A', price=Decimal('10.00'))
    product_b = Product.objects.create(restaurant=second, category=category_b, name='B', price=Decimal('20.00'))
    return first, second, category_a, category_b, product_a, product_b


def runtime_role():
    with connection.cursor() as cursor:
        cursor.execute('SET LOCAL ROLE tavvo_app')


def test_runtime_is_not_owner_superuser_or_bypass(tenants):
    runtime_role()
    with connection.cursor() as cursor:
        cursor.execute('SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user')
        assert cursor.fetchone() == (False, False)
        cursor.execute("SELECT tableowner FROM pg_tables WHERE tablename='catalog_product'")
        assert cursor.fetchone()[0] != 'tavvo_app'


def test_rls_fails_closed_without_scope_and_switches_tenant(tenants):
    a, b, ca, cb, pa, pb = tenants
    runtime_role()
    assert not Product.objects.exists()
    set_tenant(a.id)
    assert list(Product.objects.values_list('id', flat=True)) == [pa.id]
    assert Product.objects.filter(id=pb.id).update(name='attacked') == 0
    assert Product.objects.filter(id=pb.id).delete()[0] == 0
    set_tenant(b.id)
    assert list(Product.objects.values_list('id', flat=True)) == [pb.id]


def test_rls_rejects_insert_and_tenant_reassignment(tenants):
    a, b, ca, cb, pa, pb = tenants
    runtime_role()
    set_tenant(a.id)
    with pytest.raises(DatabaseError), transaction.atomic():
        Product.objects.create(restaurant=b, category=cb, name='forbidden', price='1.00')
    with pytest.raises(DatabaseError), transaction.atomic():
        Product.objects.filter(id=pa.id).update(restaurant=b, category=cb)


def test_composite_foreign_key_even_without_rls(tenants):
    a, b, ca, cb, pa, pb = tenants
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.create(restaurant=a, category=cb, name='invalid relation', price='1.00')


@pytest.mark.django_db(transaction=True)
def test_transaction_context_does_not_leak_to_next_connection_use():
    with transaction.atomic():
        runtime_role()
        set_tenant('00000000-0000-0000-0000-000000000001')
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('tavvo.restaurant_id', true)")
            assert cursor.fetchone()[0].endswith('1')
    with transaction.atomic():
        runtime_role()
        with connection.cursor() as cursor:
            cursor.execute("SELECT NULLIF(current_setting('tavvo.restaurant_id', true), '')")
            assert cursor.fetchone()[0] is None


def test_audit_is_append_only_for_runtime(tenants):
    a, *_ = tenants
    runtime_role()
    set_tenant(a.id)
    with pytest.raises(DatabaseError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM audit_auditlog')
