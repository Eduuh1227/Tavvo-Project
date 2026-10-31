from django.db import migrations


TABLES = ('commerce_ordersettings', 'commerce_order', 'commerce_orderitem', 'commerce_subscription')


def apply(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
            cursor.execute(f'''CREATE POLICY tenant_scope ON {table}
                USING (restaurant_id::text = NULLIF(current_setting('tavvo.restaurant_id', true), ''))
                WITH CHECK (restaurant_id::text = NULLIF(current_setting('tavvo.restaurant_id', true), ''))''')
        for column, target in (('order_id', 'commerce_order'), ('product_id', 'catalog_product')):
            cursor.execute(f'''ALTER TABLE commerce_orderitem ADD CONSTRAINT item_{column}_same_tenant
                FOREIGN KEY (restaurant_id, {column}) REFERENCES {target}(restaurant_id, id)
                DEFERRABLE INITIALLY IMMEDIATE''')
        cursor.execute('''DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='tavvo_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON commerce_ordersettings, commerce_order,
                commerce_orderitem, commerce_subscription, commerce_stripebinding, commerce_webhookreceipt TO tavvo_app;
            END IF; END $$''')


def reverse(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for column in ('order_id', 'product_id'):
            cursor.execute(f'ALTER TABLE commerce_orderitem DROP CONSTRAINT item_{column}_same_tenant')
        for table in TABLES:
            cursor.execute(f'DROP POLICY tenant_scope ON {table}')
            cursor.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [('commerce', '0001_initial'), ('core', '0001_tenant_integrity')]
    operations = [migrations.RunPython(apply, reverse)]
