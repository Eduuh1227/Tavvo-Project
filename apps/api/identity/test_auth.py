import base64
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_otp.oath import TOTP
from rest_framework.test import APIClient

from identity.models import PasswordResetDelivery, RecoveryCode, TotpDevice, User
from identity.security import cipher, consume_limit, verify_mfa
from restaurants.models import Restaurant, RestaurantMembership

pytestmark = pytest.mark.django_db
PASSWORD = "Tavvo-test-password-8723!"


@pytest.fixture(autouse=True)
def auth_settings(settings):
    settings.TAVVO_MFA_ENCRYPTION_KEY = Fernet.generate_key().decode()
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.TAVVO_PASSWORD_RESET_URL = "https://admin.example.test/reset-password"
    settings.CSRF_FAILURE_VIEW = "identity.views.csrf_failure"
    settings.PASSWORD_RESET_TIMEOUT = 1800


@pytest.fixture
def user():
    return User.objects.create_user(email="manager@example.test", password=PASSWORD, name="Manager")


@pytest.fixture
def client():
    return APIClient(enforce_csrf_checks=True)


def csrf(client):
    response = client.get("/v1/auth/csrf/")
    assert response.status_code == 200
    client.credentials(HTTP_X_CSRFTOKEN=response.json()["csrfToken"])


def sign_in(client, user, otp=None):
    csrf(client)
    data = {"email": user.email, "password": PASSWORD}
    if otp:
        data["otp"] = otp
    response = client.post("/v1/auth/login/", data, format="json")
    csrf(client)
    return response


def privileged_session(client, user):
    client.force_login(user)
    session = client.session
    session.update({"auth_started_at": int(timezone.now().timestamp()), "auth_seen_at": int(timezone.now().timestamp()), "auth_version": user.session_version, "mfa_verified": True})
    session.save()
    csrf(client)


def test_login_requires_csrf_and_normalizes_email(client, user):
    response = client.post("/v1/auth/login/", {"email": user.email, "password": PASSWORD}, format="json")
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    csrf(client)
    response = client.post("/v1/auth/login/", {"email": user.email.upper(), "password": PASSWORD}, format="json")
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert "password" not in response.json()


def test_credentials_failure_is_generic_and_account_limit_is_shared(user):
    for index in range(13):
        client = APIClient(enforce_csrf_checks=True)
        csrf(client)
        response = client.post("/v1/auth/login/", {"email": user.email, "password": "wrong-password"}, format="json", REMOTE_ADDR=f"192.0.2.{index}")
        assert response.status_code == (401 if index < 12 else 429)
    unknown = APIClient(enforce_csrf_checks=True)
    csrf(unknown)
    response = unknown.post("/v1/auth/login/", {"email": "unknown@example.test", "password": PASSWORD}, format="json")
    assert response.json() == {"code": "invalid_credentials", "message": "E-mail ou senha inválidos."}


def test_me_filters_revoked_memberships_and_logout_revokes_cookie(client, user):
    first = Restaurant.objects.create(name="First", slug="first")
    second = Restaurant.objects.create(name="Second", slug="second")
    RestaurantMembership.objects.create(user=user, restaurant=first, role="manager")
    RestaurantMembership.objects.create(user=user, restaurant=second, status="revoked")
    assert sign_in(client, user).status_code == 200
    response = client.get("/v1/me/restaurants/")
    assert [m["restaurant"]["id"] for m in response.json()] == [str(first.id)]
    stolen_cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
    assert Session.objects.filter(session_key=stolen_cookie).exists()
    assert client.post("/v1/auth/logout/", {}, format="json").status_code == 204
    assert not Session.objects.filter(session_key=stolen_cookie).exists()
    client.cookies[settings.SESSION_COOKIE_NAME] = stolen_cookie
    assert client.get("/v1/auth/me/").status_code in (401, 403)


@pytest.mark.parametrize("revocation", ["version", "idle", "absolute"])
def test_session_expiration_and_revocation(client, user, revocation, settings):
    settings.TAVVO_SESSION_ABSOLUTE_SECONDS = 3600
    settings.TAVVO_SESSION_IDLE_SECONDS = 600
    sign_in(client, user)
    if revocation == "version":
        user.session_version += 1
        user.save(update_fields=["session_version"])
    else:
        session = client.session
        key = "auth_seen_at" if revocation == "idle" else "auth_started_at"
        session[key] = int(timezone.now().timestamp()) - (601 if revocation == "idle" else 3601)
        session.save()
    assert client.get("/v1/auth/me/").status_code in (401, 403)


def test_admin_mfa_enrollment_replay_and_single_use_recovery(client):
    user = User.objects.create_user(email="admin@example.test", password=PASSWORD, name="Admin", is_platform_admin=True)
    assert sign_in(client, user).json() == {"mfa_enrollment_required": True}
    assert client.get("/v1/platform/users/").status_code == 403
    enrollment = client.post("/v1/auth/mfa/enroll/", {}, format="json")
    assert enrollment.status_code == 200
    secret = enrollment.json()["secret"]
    assert secret not in TotpDevice.objects.get(user=user).encrypted_secret
    totp = TOTP(base64.b32decode(secret))
    code = f"{totp.token():06d}"
    confirmation = client.post("/v1/auth/mfa/confirm/", {"otp": code}, format="json")
    assert confirmation.status_code == 200
    recovery = confirmation.json()["recovery_codes"][0]
    assert not RecoveryCode.objects.filter(password_hash=recovery).exists()
    assert client.get("/v1/platform/users/").status_code == 200
    assert client.post("/v1/auth/mfa/enroll/", {}, format="json").status_code == 409
    assert client.post("/v1/auth/logout/", {}, format="json").status_code == 204
    assert sign_in(client, user).json() == {"mfa_required": True}
    replay = sign_in(client, user, code)
    assert replay.status_code == 401
    assert sign_in(client, user, recovery).status_code == 200
    assert RecoveryCode.objects.filter(user=user, used_at__isnull=False).count() == 1
    assert client.post("/v1/auth/logout/", {}, format="json").status_code == 204
    assert sign_in(client, user, recovery).status_code == 401


def test_reset_is_non_enumerating_single_use_and_revokes_sessions(client, user):
    other = APIClient(enforce_csrf_checks=True)
    assert sign_in(other, user).status_code == 200
    csrf(client)
    known = client.post("/v1/auth/password-reset/request/", {"email": user.email}, format="json")
    unknown = client.post("/v1/auth/password-reset/request/", {"email": "unknown@example.test"}, format="json")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert PasswordResetDelivery.objects.count() == 2
    call_command("process_auth_mail")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    url = re.search(r"https://\S+", mail.outbox[0].body).group(0)
    params = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}
    params["password"] = "Changed-strong-password-9247!"
    assert client.post("/v1/auth/password-reset/confirm/", params, format="json").status_code == 204
    csrf(client)
    assert client.post("/v1/auth/password-reset/confirm/", params, format="json").status_code == 400
    assert other.get("/v1/auth/me/").status_code in (401, 403)
    user.refresh_from_db()
    assert user.check_password(params["password"])


def test_reset_delivery_expiry_does_not_send_old_links(user):
    delivery = PasswordResetDelivery.objects.create(email=user.email)
    PasswordResetDelivery.objects.filter(pk=delivery.pk).update(created_at=timezone.now() - timedelta(minutes=16))
    call_command("process_auth_mail")
    assert not getattr(mail, "outbox", [])
    delivery.refresh_from_db()
    assert delivery.processed_at is not None


def test_user_management_requires_mfa_and_revoke_invalidates_target(client, user):
    assert sign_in(client, user).status_code == 200
    assert client.get("/v1/platform/users/").status_code == 403
    admin = User.objects.create_user(email="admin@example.test", password=PASSWORD, name="Admin", is_platform_admin=True)
    admin_client = APIClient(enforce_csrf_checks=True)
    privileged_session(admin_client, admin)
    response = admin_client.post("/v1/platform/users/", {"email": "NEW@example.test", "name": "New", "password": PASSWORD}, format="json")
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.test"
    assert admin_client.patch(f"/v1/platform/users/{admin.id}/", {"is_platform_admin": False}, format="json").status_code == 409
    assert admin_client.post(f"/v1/platform/users/{user.id}/revoke-sessions/", {}, format="json").status_code == 204
    assert client.get("/v1/auth/me/").status_code in (401, 403)


@pytest.mark.django_db(transaction=True)
def test_rate_limit_is_atomic_across_parallel_connections():
    def attempt(_):
        close_old_connections()
        try:
            return consume_limit("parallel-test", "shared-account", 5, 60)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attempt, range(18)))
    assert sum(results) == 5


@pytest.mark.django_db(transaction=True)
def test_totp_can_be_consumed_only_once_concurrently(user):
    secret = b"a-long-unique-secret!"
    TotpDevice.objects.create(user=user, confirmed=True, encrypted_secret=cipher().encrypt(secret).decode())
    token = f"{TOTP(secret).token():06d}"

    def attempt(_):
        close_old_connections()
        try:
            return verify_mfa(user, token)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == [False, True]


def test_mfa_enrollment_revokes_sessions_opened_without_second_factor(client, user):
    previous = APIClient(enforce_csrf_checks=True)
    assert sign_in(previous, user).status_code == 200
    assert sign_in(client, user).status_code == 200
    enrollment = client.post("/v1/auth/mfa/enroll/", {}, format="json")
    secret = base64.b32decode(enrollment.json()["secret"])
    response = client.post("/v1/auth/mfa/confirm/", {"otp": f"{TOTP(secret).token():06d}"}, format="json")
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.session_version == 2
    assert client.session["auth_version"] == user.session_version
    assert client.get("/v1/auth/me/").status_code == 200
    assert previous.get("/v1/auth/me/").status_code in (401, 403)


def test_reset_rejected_password_still_consumes_rate_limit(client, user):
    csrf(client)
    payload = {"uid": urlsafe_base64_encode(force_bytes(user.pk)),
               "token": default_token_generator.make_token(user), "password": "123"}
    for _ in range(8):
        response = client.post("/v1/auth/password-reset/confirm/", payload, format="json")
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_password"
    response = client.post("/v1/auth/password-reset/confirm/", payload, format="json")
    assert response.status_code == 429
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_account_deactivation_invalidates_current_session_immediately(client, user):
    assert sign_in(client, user).status_code == 200
    admin = User.objects.create_user(email="deactivate@example.test", password=PASSWORD,
                                    name="Admin", is_platform_admin=True)
    privileged = APIClient(enforce_csrf_checks=True)
    privileged_session(privileged, admin)
    response = privileged.patch(f"/v1/platform/users/{user.id}/", {"is_active": False}, format="json")
    assert response.status_code == 200
    assert client.get("/v1/auth/me/").status_code in (401, 403)
