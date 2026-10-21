"""Provision an explicitly selected, dedicated Supabase demo, without printing secrets.

Run after connecting its free Marketplace resource and pulling development envs.
Never run this against an existing commercial database: it restricts Data API access
to the public schema. Migrations and provisioning credentials stay local.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.parse import quote, urlparse, urlunparse
import uuid

import boto3
from botocore.config import Config
from cryptography.fernet import Fernet
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]


def read_env(path):
    result = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            result[key] = json.loads(value) if value.startswith('"') else value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-ref', required=True)
    parser.add_argument('--dedicated-demo', action='store_true', required=True)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.local/vercel-supabase.env')
    args = parser.parse_args()
    source = read_env(args.env_file)
    ref = urlparse(source['SUPABASE_URL']).hostname.split('.')[0]
    if ref != args.project_ref:
        raise SystemExit('Selected Supabase project does not match the supplied environment.')
    output = ROOT / '.local/vercel-demo.env'
    previous = read_env(output) if output.exists() else {}
    owner = urlparse(source['POSTGRES_URL_NON_POOLING'])
    if ref not in (owner.username or '') or not owner.hostname.endswith('.supabase.com'):
        raise SystemExit('Expected the selected Supabase session-pooler connection.')
    owner_url = urlunparse(owner._replace(query='sslmode=require'))
    password = previous.get('TAVVO_DB_PASSWORD') or secrets.token_urlsafe(36)
    runtime_url = urlunparse(owner._replace(
        netloc=f'tavvo_app.{ref}:{quote(password, safe="")}@{owner.hostname}:6543',
        query='sslmode=require'))
    env = {
        'TAVVO_ENV': 'demo', 'VERCEL': '1', 'DATABASE_SSLMODE': 'require',
        'DATABASE_URL': runtime_url, 'MIGRATION_DATABASE_URL': owner_url,
        'TAVVO_DB_PASSWORD': password,
        'DJANGO_SECRET_KEY': previous.get('DJANGO_SECRET_KEY') or secrets.token_urlsafe(64),
        'TAVVO_MFA_ENCRYPTION_KEY': previous.get('TAVVO_MFA_ENCRYPTION_KEY') or Fernet.generate_key().decode(),
        'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1',
        'S3_ENDPOINT_URL': source['SUPABASE_URL'] + '/storage/v1/s3',
        'S3_REGION': 'sa-east-1', 'S3_BUCKET': 'tavvo-images',
        'S3_ACCESS_KEY': ref, 'S3_SECRET_KEY': source['SUPABASE_ANON_KEY'],
        'S3_SESSION_TOKEN': source['SUPABASE_SERVICE_ROLE_KEY'],
        'IMAGE_MAX_BYTES': str(4 * 1024 * 1024),
        'VITE_DEMO_MODE': 'true',
    }
    output.write_text(''.join(f'{k}={json.dumps(v)}\n' for k, v in env.items()), encoding='utf-8')
    process_env = {**os.environ, **env}
    subprocess.run([sys.executable, str(ROOT / 'infra/provision_database.py')], env=process_env, check=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/manage.py'), 'migrate', '--noinput'], env=process_env, check=True)
    with psycopg.connect(owner_url) as conn:
        # Supabase's REST/GraphQL API must not expose Django sessions, identity or catalog.
        conn.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC, anon, authenticated, service_role')
        conn.execute('GRANT USAGE ON SCHEMA public TO tavvo_app')
        conn.execute('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated, service_role')
        conn.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated, service_role')
        tables = conn.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public'").fetchall()
        for name, rls in tables:
            if not rls:
                conn.execute(sql.SQL('ALTER TABLE {} ENABLE ROW LEVEL SECURITY').format(sql.Identifier(name)))
                conn.execute(sql.SQL('CREATE POLICY app_access ON {} TO tavvo_app USING (true) WITH CHECK (true)').format(sql.Identifier(name)))
        conn.execute('REVOKE UPDATE, DELETE, TRUNCATE ON audit_auditlog FROM tavvo_app')
    with psycopg.connect(runtime_url, prepare_threshold=None) as conn:
        role = conn.execute('SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
        assert role == ('tavvo_app', False, False), role
        assert conn.execute('SELECT count(*) FROM catalog_product').fetchone()[0] == 0
    storage = boto3.client('s3', endpoint_url=env['S3_ENDPOINT_URL'],
        aws_access_key_id=env['S3_ACCESS_KEY'], aws_secret_access_key=env['S3_SECRET_KEY'],
        aws_session_token=env['S3_SESSION_TOKEN'], region_name=env['S3_REGION'],
        config=Config(signature_version='s3v4', s3={'addressing_style': 'path'},
            request_checksum_calculation='when_required', response_checksum_validation='when_required'))
    if env['S3_BUCKET'] not in [row['Name'] for row in storage.list_buckets()['Buckets']]:
        storage.create_bucket(Bucket=env['S3_BUCKET'])
    key = f'verification/{uuid.uuid4()}.txt'
    storage.put_object(Bucket=env['S3_BUCKET'], Key=key, Body=b'tavvo-storage-check')
    assert storage.get_object(Bucket=env['S3_BUCKET'], Key=key)['Body'].read() == b'tavvo-storage-check'
    storage.delete_object(Bucket=env['S3_BUCKET'], Key=key)
    print('Demo database migrated; restricted runtime role, Data API isolation and private storage verified.')
    print('Environment written to ignored .local/vercel-demo.env; no credentials printed.')


if __name__ == '__main__':
    main()
