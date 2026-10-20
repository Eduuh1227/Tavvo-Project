from django.db import migrations

TENANT_TABLES = (
    'restaurants_restaurantsettings', 'catalog_category', 'catalog_product',
    'catalog_productimage', 'tables_menutable',
)


def apply(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute('''ALTER TABLE catalog_product ADD CONSTRAINT product_category_same_tenant
        FOREIGN KEY (restaurant_id, category_id) REFERENCES catalog_category(restaurant_id, id)
        DEFERRABLE INITIALLY IMMEDIATE''')
    cursor.execute('''ALTER TABLE catalog_productimage ADD CONSTRAINT image_product_same_tenant
        FOREIGN KEY (restaurant_id, product_id) REFERENCES catalog_product(restaurant_id, id)
        DEFERRABLE INITIALLY IMMEDIATE''')
    for table in TENANT_TABLES:
        cursor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
        cursor.execute(f'''CREATE POLICY tenant_scope ON {table}
            USING (restaurant_id::text = NULLIF(current_setting('tavvo.restaurant_id', true), ''))
            WITH CHECK (restaurant_id::text = NULLIF(current_setting('tavvo.restaurant_id', true), ''))''')
    cursor.execute('ALTER TABLE audit_auditlog ENABLE ROW LEVEL SECURITY')
    cursor.execute('ALTER TABLE audit_auditlog FORCE ROW LEVEL SECURITY')
    cursor.execute('''CREATE POLICY audit_scope ON audit_auditlog
        USING (restaurant_id::text = NULLIF(current_setting('tavvo.restaurant_id', true), ''))
        WITH CHECK (restaurant_id IS NULL OR restaurant_id::text = NULLIF(current_setting('tavvo.restaurant_id', true), ''))''')
    # Development and CI create this role before migrations. Production may provision it later.
    cursor.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='tavvo_app') THEN
        GRANT USAGE ON SCHEMA public TO tavvo_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tavvo_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tavvo_app;
        REVOKE UPDATE, DELETE ON audit_auditlog FROM tavvo_app;
        END IF; END $$""")


def reverse(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute('ALTER TABLE catalog_product DROP CONSTRAINT product_category_same_tenant')
    cursor.execute('ALTER TABLE catalog_productimage DROP CONSTRAINT image_product_same_tenant')
    for table in (*TENANT_TABLES, 'audit_auditlog'):
        policy = 'audit_scope' if table == 'audit_auditlog' else 'tenant_scope'
        cursor.execute(f'DROP POLICY {policy} ON {table}')
        cursor.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0002_initial'), ('restaurants', '0001_initial'),
        ('tables', '0001_initial'), ('audit', '0002_initial'),
        ('sessions', '0001_initial'),
    ]
    operations = [migrations.RunPython(apply, reverse)]
