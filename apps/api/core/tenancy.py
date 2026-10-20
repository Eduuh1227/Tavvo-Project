"""A transaction-local scope never survives connection reuse."""
from django.db import connection


def set_tenant(restaurant_id):
    if not connection.in_atomic_block:
        raise RuntimeError('Tenant queries require an explicit database transaction')
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('tavvo.restaurant_id', %s, true)", [str(restaurant_id)])


def clear_tenant():
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('tavvo.restaurant_id', '', true)")
