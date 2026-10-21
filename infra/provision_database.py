"""Idempotent local/CI provisioning; run only with the migration owner's connection."""
import os

import psycopg
from psycopg import sql


def main():
    owner_url = os.environ['MIGRATION_DATABASE_URL']
    password = os.environ['TAVVO_DB_PASSWORD']
    with psycopg.connect(owner_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'tavvo_app'")
        if cursor.fetchone() is None:
            cursor.execute('CREATE ROLE tavvo_app')
        # Managed PostgreSQL owners cannot spell SUPERUSER/REPLICATION/BYPASSRLS
        # even when disabling them. New roles default to false; reject unsafe
        # existing roles instead of requiring superuser privileges to alter them.
        cursor.execute("SELECT rolsuper, rolreplication, rolbypassrls FROM pg_roles WHERE rolname = 'tavvo_app'")
        if any(cursor.fetchone()):
            raise RuntimeError('Runtime role must not have elevated PostgreSQL privileges.')
        cursor.execute(sql.SQL('ALTER ROLE tavvo_app LOGIN NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD {}').format(sql.Literal(password)))
        cursor.execute('SELECT current_database(), current_user')
        database, owner = cursor.fetchone()
        if owner == 'tavvo_app':
            raise RuntimeError('Provisioning requires a separate database owner.')
        cursor.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO tavvo_app').format(sql.Identifier(database)))
        cursor.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        cursor.execute('GRANT USAGE ON SCHEMA public TO tavvo_app')
        cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tavvo_app').format(sql.Identifier(owner)))
        cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO tavvo_app').format(sql.Identifier(owner)))
        # Repeat bootstrap after migrations without restoring audit mutation privileges.
        cursor.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tavvo_app')
        cursor.execute('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tavvo_app')
        cursor.execute("SELECT to_regclass('public.audit_auditlog')")
        if cursor.fetchone()[0]:
            cursor.execute('REVOKE UPDATE, DELETE, TRUNCATE ON audit_auditlog FROM tavvo_app')
    print('Runtime role provisioned with no ownership or RLS bypass privileges.')


if __name__ == '__main__':
    main()
