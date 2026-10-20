"""Snapshot/compare the local demo across a service restart without reseeding."""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
import requests

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'apps/api'))
from core.environment import load_local_environment

load_local_environment()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('mode', choices=['snapshot', 'verify'])
args = parser.parse_args()
base = os.getenv('TAVVO_API_URL', 'http://127.0.0.1:8000').rstrip('/')
site = os.getenv('TAVVO_E2E_PUBLIC_URL', 'http://localhost:3000').rstrip('/')
if os.getenv('TAVVO_ENV') != 'development' or any(urlsplit(url).hostname not in ('localhost', '127.0.0.1') for url in (base, site)):
    raise SystemExit('Persistence verification is restricted to local development.')
local = root / '.local'
credentials = json.loads((local / 'demo-credentials.json').read_text())
records = json.loads((local / 'demo-records.json').read_text())
snapshot = {}
with psycopg.connect(os.environ['DATABASE_URL']) as connection:
    role, superuser, bypass = connection.execute(
        'SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user'
    ).fetchone()
    if role != 'tavvo_app' or superuser or bypass:
        raise SystemExit('Verification requires the restricted tavvo_app runtime role.')

for tenant in ('a', 'b'):
    session = requests.Session()
    session.get(f'{base}/v1/auth/csrf/', timeout=15).raise_for_status()
    response = session.post(f'{base}/v1/auth/login/', json={
        'email': credentials[f'manager_{tenant}'], 'password': credentials['password'],
    }, headers={'X-CSRFToken': session.cookies['csrftoken']}, timeout=15)
    response.raise_for_status()
    restaurant = records[tenant]['restaurant']
    prefix = f'{base}/v1/restaurants/{restaurant["id"]}'
    result = {}
    for resource in ('categories', 'products', 'tables', 'settings'):
        url = f'{prefix}/{resource}/'
        data = []
        while url:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            page = response.json()
            if resource == 'settings':
                data = page
                break
            data.extend(page['results'])
            url = page['next']
        result[resource] = data
    response = requests.get(f'{base}/v1/public/restaurants/{restaurant["slug"]}/menu/', timeout=15)
    response.raise_for_status()
    result['public_menu'] = response.json()
    page = requests.get(f'{site}/r/{restaurant["slug"]}', timeout=60)
    page.raise_for_status()
    if restaurant['name'] not in page.text:
        raise SystemExit(f'Public site did not render restaurant {tenant.upper()}.')
    session.post(f'{base}/v1/auth/logout/', json={}, headers={
        'X-CSRFToken': session.cookies['csrftoken'],
    }, timeout=15).raise_for_status()
    snapshot[tenant] = result

path = local / 'persistence-snapshot.json'
if args.mode == 'snapshot':
    path.write_text(json.dumps(snapshot, sort_keys=True), encoding='utf-8')
    print('Saved API snapshot for A/B: restaurants, categories, products, settings and tables.')
else:
    expected = json.loads(path.read_text(encoding='utf-8'))
    if snapshot != expected:
        raise SystemExit('Persisted API data differs from the pre-restart snapshot.')
    print('PASS: exact A/B API data survived restart; both public sites render; runtime role has no RLS bypass.')
