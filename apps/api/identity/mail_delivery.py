"""Durable recovery outbox. Queue messages contain only a random delivery ID."""
import logging
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import PasswordResetDelivery, User


def enqueue_recovery(delivery_id):
    if not settings.TAVVO_RECOVERY_QUEUE_ENABLED:
        return
    try:
        from vercel.queue.sync import send
        send('tavvo-password-recovery', {'delivery_id': str(delivery_id)},
             idempotency_key=str(delivery_id), retention=900)
    except Exception:
        # The outbox remains recoverable with process_auth_mail. Never log SDK secrets.
        logging.getLogger(__name__).error('Recovery queue enqueue failed; outbox retained')


def process_delivery(delivery_id):
    failed = False
    with transaction.atomic():
        delivery = PasswordResetDelivery.objects.select_for_update().filter(pk=delivery_id).first()
        if not delivery or delivery.processed_at or delivery.attempts >= 5:
            return
        user = User.objects.filter(email__iexact=delivery.email, is_active=True).first()
        try:
            if user and user.has_usable_password() and delivery.created_at > timezone.now() - timedelta(minutes=15):
                params = urlencode({'uid': urlsafe_base64_encode(force_bytes(user.pk)), 'token': default_token_generator.make_token(user)})
                url = f'{settings.TAVVO_PASSWORD_RESET_URL}?{params}'
                send_mail('Recuperação de acesso — Tavvo', f'Para redefinir sua senha, acesse:\n\n{url}\n\nSe não solicitou esta alteração, ignore esta mensagem.',
                          settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            delivery.processed_at = timezone.now()
        except Exception:
            delivery.attempts += 1
            failed = True
        delivery.save(update_fields=['processed_at', 'attempts'])
    if failed:
        # Commit attempt count, then request a bounded queue retry without leaking SMTP errors.
        raise RuntimeError('Recovery delivery temporarily unavailable') from None
