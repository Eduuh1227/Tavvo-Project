import base64
import secrets
from urllib.parse import quote

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django_otp.oath import TOTP

from .models import AuthRateLimit, RecoveryCode, TotpDevice


def cipher():
    key = getattr(settings, "TAVVO_MFA_ENCRYPTION_KEY", "")
    if not key:
        raise ImproperlyConfigured("TAVVO_MFA_ENCRYPTION_KEY must contain a Fernet key")
    return Fernet(key.encode() if isinstance(key, str) else key)


def consume_limit(namespace, identity, limit, seconds):
    key = salted_hmac("tavvo.auth.rate-limit", f"{namespace}:{identity}", algorithm="sha256").hexdigest()
    now = timezone.now()
    with transaction.atomic():
        AuthRateLimit.objects.get_or_create(key=key, defaults={"started_at": now})
        bucket = AuthRateLimit.objects.select_for_update().get(key=key)
        if (now - bucket.started_at).total_seconds() >= seconds:
            bucket.started_at, bucket.count = now, 0
        bucket.count += 1
        bucket.save(update_fields=["started_at", "count"])
        return bucket.count <= limit


def limits_allow(request, purpose, account=""):
    # REMOTE_ADDR is trusted only after normalization by the deployment proxy.
    ip = request.META.get("REMOTE_ADDR", "unknown")
    if purpose == "login":
        specs = [("ip", ip, 40, 900), ("account", account, 12, 900)]
    elif purpose == "reset":
        specs = [("ip", ip, 20, 3600), ("account", account, 5, 3600)]
    else:
        specs = [("ip", ip, 30, 300), ("account", account, 8, 300)]
    allowed = [consume_limit(f"{purpose}:{kind}", who, count, span) for kind, who, count, span in specs]
    return all(allowed)


@transaction.atomic
def enrollment_details(user):
    secret = secrets.token_bytes(20)
    TotpDevice.objects.get_or_create(user=user, defaults={"encrypted_secret": cipher().encrypt(secret).decode()})
    device = TotpDevice.objects.select_for_update().get(user=user)
    if device.confirmed:
        return None
    secret = cipher().decrypt(device.encrypted_secret.encode())
    encoded = base64.b32encode(secret).decode().rstrip("=")
    uri = f"otpauth://totp/{quote('Tavvo:' + user.email, safe='')}?secret={encoded}&issuer=Tavvo&algorithm=SHA1&digits=6&period=30"
    return {"secret": encoded, "otpauth_url": uri}


def verify_totp_locked(device, code):
    if not isinstance(code, str) or not code.isascii() or not code.isdigit() or len(code) != 6:
        return False
    totp = TOTP(cipher().decrypt(device.encrypted_secret.encode()), drift=device.drift)
    totp.time = timezone.now().timestamp()
    if not totp.verify(int(code), tolerance=1, min_t=device.last_t + 1):
        return False
    device.last_t, device.drift = totp.t(), totp.drift
    device.save(update_fields=["last_t", "drift"])
    return True


@transaction.atomic
def verify_mfa(user, code):
    device = TotpDevice.objects.select_for_update().filter(user=user, confirmed=True).first()
    if device is None:
        return False
    if verify_totp_locked(device, code):
        return True
    # The device row serializes both TOTP and recovery-code consumption.
    for recovery in RecoveryCode.objects.filter(user=user, used_at__isnull=True):
        if check_password(code, recovery.password_hash):
            recovery.used_at = timezone.now()
            recovery.save(update_fields=["used_at"])
            return True
    return False


def issue_recovery_codes(user):
    """Caller holds the user's device row lock; plaintext is returned once."""
    codes = [secrets.token_hex(8) for _ in range(8)]
    RecoveryCode.objects.filter(user=user).delete()
    RecoveryCode.objects.bulk_create([RecoveryCode(user=user, password_hash=make_password(code)) for code in codes])
    return codes
