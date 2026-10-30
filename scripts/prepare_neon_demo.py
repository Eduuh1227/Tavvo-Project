"""Configure a dedicated Neon demo using locally pulled secrets; never print them."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.parse import quote, urlparse, urlunparse

import psycopg
from prepare_vercel_demo import read_env

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dedicated-demo', action='store_true', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    args = parser.parse_args()
    source = read_env(args.env_file)
    previous = read_env(ROOT / '.local/vercel-demo.env')
    output = ROOT / '.local/vercel-neon-demo.env'
    saved = read_env(output) if output.exists() else {}
    direct = urlparse(source['NEON_DATABASE_URL_UNPOOLED'])
    pooled = urlparse(source['NEON_DATABASE_URL'])
    if not all((u.hostname or '').endswith('.neon.tech') for u in (direct, pooled)):
        raise SystemExit('Expected dedicated Neon connections.')
    if '-pooler' in direct.hostname or '-pooler' not in pooled.hostname:
        raise SystemExit('Expected separate direct migration and pooled runtime connections.')
    password = saved.get('TAVVO_DB_PASSWORD') or secrets.token_urlsafe(36)
    runtime = urlunparse(pooled._replace(
        netloc=f'tavvo_app:{quote(password, safe="")}@{pooled.hostname}:{pooled.port or 5432}',
        query='sslmode=require'))
    env = {k: v for k, v in previous.items() if not k.startswith('S3_')}
    env.update({
        'TAVVO_ENV': 'demo', 'DATABASE_URL': runtime,
        'MIGRATION_DATABASE_URL': source['NEON_DATABASE_URL_UNPOOLED'],
        'TAVVO_DB_PASSWORD': password, 'DATABASE_SSLMODE': 'require',
        'IMAGE_STORAGE_BACKEND': 'vercel_blob',
        'BLOB_READ_WRITE_TOKEN': source['BLOB_READ_WRITE_TOKEN'],
    })
    output.write_text(''.join(f'{k}={json.dumps(v)}\n' for k, v in env.items()), encoding='utf-8')
    process_env = {**os.environ, **env}
    subprocess.run([sys.executable, str(ROOT / 'infra/provision_database.py')], env=process_env, check=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/manage.py'), 'migrate', '--noinput'], env=process_env, check=True)
    subprocess.run([sys.executable, str(ROOT / 'infra/provision_database.py')], env=process_env, check=True)
    with psycopg.connect(runtime, connect_timeout=15, prepare_threshold=None) as conn:
        role = conn.execute('SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
        assert role == ('tavvo_app', False, False), 'Unsafe runtime role'
        assert conn.execute('SELECT count(*) FROM catalog_product').fetchone()[0] == 0, 'Tenant isolation failed'
        assert not conn.execute("SELECT has_table_privilege(current_user, 'audit_auditlog', 'DELETE')").fetchone()[0]
    print('Neon migrations complete; restricted role, tenant isolation and audit permissions verified.')
    print('Runtime and migration secrets saved only in ignored .local/vercel-neon-demo.env.')


if __name__ == '__main__':
    main()
