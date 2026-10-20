"""Populate an explicitly local demonstration through the real HTTP API.

Only the initial platform account is bootstrapped directly. Everything else
uses authentication, MFA, authorization and the same endpoints as the panels.
Credentials are written to ignored .local/ and never printed.
"""
import base64
import json
import os
import secrets
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django

django.setup()
from django.conf import settings
from django_otp.oath import TOTP
from identity.models import User, TotpDevice
from identity.security import cipher

if settings.ENVIRONMENT != 'development':
    raise SystemExit('Demo data is only allowed in development.')
base = os.getenv('TAVVO_API_URL', 'http://127.0.0.1:8000').rstrip('/')
if not base.startswith(('http://127.0.0.1:', 'http://localhost:')):
    raise SystemExit('Demo provisioning is restricted to loopback.')
local = ROOT / '.local'
local.mkdir(exist_ok=True)
credentials_path = local / 'demo-credentials.json'
old = json.loads(credentials_path.read_text()) if credentials_path.exists() else {}
password = os.getenv('TAVVO_E2E_PASSWORD') or old.get('password') or secrets.token_urlsafe(24)
admin_email = 'admin@example.test'
admin, created = User.objects.get_or_create(email=admin_email, defaults={'name': 'Tavvo Demo', 'is_platform_admin': True})
if created:
    admin.set_password(password)
    admin.save()


def request(session, method, path, data=None, files=None):
    headers = {'X-CSRFToken': session.cookies.get('csrftoken', '')}
    response = session.request(method, base + '/v1/' + path, json=data if not files else None,
                               files=files, headers=headers, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(f'{method} {path} failed with HTTP {response.status_code}: {response.text[:300]}')
    return response.json() if response.content else None


def login(email, otp=None):
    session = requests.Session()
    request(session, 'GET', 'auth/csrf/')
    result = request(session, 'POST', 'auth/login/', {'email': email, 'password': password, **({'otp': otp} if otp else {})})
    return session, result


def rows(result):
    return result['results'] if isinstance(result, dict) else result


device = TotpDevice.objects.filter(user=admin, confirmed=True).first()
otp = None
if device:
    current = int(time.time()) // 30
    if current <= device.last_t:
        time.sleep((device.last_t + 1) * 30 - time.time() + 0.2)
    otp = str(TOTP(cipher().decrypt(device.encrypted_secret.encode())).token()).zfill(6)
platform, state = login(admin_email, otp)
if state.get('mfa_enrollment_required'):
    enrollment = request(platform, 'POST', 'auth/mfa/enroll/', {})
    key = enrollment['secret']
    key += '=' * (-len(key) % 8)
    code = str(TOTP(base64.b32decode(key)).token()).zfill(6)
    confirmation = request(platform, 'POST', 'auth/mfa/confirm/', {'otp': code})
    old['recovery_codes'] = confirmation['recovery_codes']

existing_restaurants = rows(request(platform, 'GET', 'platform/restaurants/'))
existing_users = rows(request(platform, 'GET', 'platform/users/'))
results = {}
for suffix in ('a', 'b'):
    slug = f'restaurante-{suffix}'
    restaurant = next((row for row in existing_restaurants if row['slug'] == slug), None)
    if restaurant is None:
        restaurant = request(platform, 'POST', 'platform/restaurants/', {'name': f'Restaurante {suffix.upper()}', 'slug': slug})
    rid = restaurant['id']
    email = f'gestor-{suffix}@example.test'
    user = next((row for row in existing_users if row['email'] == email), None)
    if user is None:
        user = request(platform, 'POST', 'platform/users/', {'email': email, 'name': f'Gestor {suffix.upper()}', 'password': password})
    memberships = rows(request(platform, 'GET', f'platform/restaurants/{rid}/memberships/'))
    if not any(row['user'] == user['id'] for row in memberships):
        request(platform, 'POST', f'platform/restaurants/{rid}/memberships/', {'user': user['id'], 'role': 'manager', 'status': 'active'})
    manager, _ = login(email)
    categories = rows(request(manager, 'GET', f'restaurants/{rid}/categories/'))
    names = ['Entradas', 'Pratos', 'Bebidas'] if suffix == 'a' else ['Especiais B', 'Bebidas B']
    for index, name in enumerate(names):
        if not any(row['name'] == name for row in categories):
            categories.append(request(manager, 'POST', f'restaurants/{rid}/categories/', {'name': name, 'sort_order': index, 'is_published': True}))
    products = rows(request(manager, 'GET', f'restaurants/{rid}/products/'))
    product_names = ['Salada da casa', 'Risoto de cogumelos', 'Peixe grelhado', 'Suco natural', 'Água mineral'] if suffix == 'a' else ['Especial do Restaurante B', 'Sobremesa B', 'Suco B']
    for index, name in enumerate(product_names):
        if not any(row['name'] == name for row in products):
            products.append(request(manager, 'POST', f'restaurants/{rid}/products/', {
                'name': name, 'category': categories[index % len(names)]['id'], 'price': f'{15 + index * 7}.90',
                'currency': 'BRL', 'is_available': True, 'is_published': True,
            }))
    results[suffix] = {'restaurant': restaurant, 'products': products, 'user': user}
    menu = request(manager, 'GET', f'public/restaurants/{slug}/menu/')
    assert menu['restaurant']['slug'] == slug
    if suffix == 'a':
        tables = rows(request(manager, 'GET', f'restaurants/{rid}/tables/'))
        if not any(row['label'] == 'Mesa 05' for row in tables):
            request(manager, 'POST', f'restaurants/{rid}/tables/', {'label': 'Mesa 05'})

# The private cookie is written only to ignored local test state, never to Git.
cookie_state = {'cookies': [], 'origins': []}
for cookie in platform.cookies:
    cookie_state['cookies'].append({
        'name': cookie.name, 'value': cookie.value, 'domain': 'localhost', 'path': '/',
        'expires': cookie.expires or -1, 'httpOnly': cookie.name == 'tavvo_session',
        'secure': False, 'sameSite': 'Lax',
    })
(local / 'admin-storage-state.json').write_text(json.dumps(cookie_state))
credentials_path.write_text(json.dumps({**old, 'password': password, 'admin_email': admin_email,
                                       'manager_a': 'gestor-a@example.test', 'manager_b': 'gestor-b@example.test'}))
(local / 'demo-records.json').write_text(json.dumps(results))
print('Demo provisioned through HTTP API: restaurants A/B, distinct managers, 3+2 categories, 5+3 products and Mesa 05.')
print('Local credentials and browser test state are in ignored .local/.')
