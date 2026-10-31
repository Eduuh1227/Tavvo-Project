from unittest.mock import patch
import pytest
from django.core import mail
from .models import PasswordResetDelivery, User
from .mail_delivery import enqueue_recovery, process_delivery

pytestmark = pytest.mark.django_db


def test_mail_replay_is_idempotent_and_failed_attempts_persist(settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    user = User.objects.create_user(email='delivery@example.test', password='Test-Password123!')
    delivery = PasswordResetDelivery.objects.create(email=user.email)
    with patch('identity.mail_delivery.send_mail', side_effect=OSError('SMTP down')):
        with pytest.raises(RuntimeError, match='temporarily unavailable'):
            process_delivery(delivery.id)
    delivery.refresh_from_db()
    assert delivery.attempts == 1 and delivery.processed_at is None
    process_delivery(delivery.id)
    process_delivery(delivery.id)
    assert len(mail.outbox) == 1
    delivery.refresh_from_db()
    assert delivery.processed_at is not None


def test_queue_payload_has_no_address_or_token(settings):
    settings.TAVVO_RECOVERY_QUEUE_ENABLED = True
    delivery = PasswordResetDelivery.objects.create(email='unknown@example.test')
    with patch('vercel.queue.sync.send') as send:
        enqueue_recovery(delivery.id)
        assert send.call_args.args == ('tavvo-password-recovery', {'delivery_id': str(delivery.id)})
    with patch('vercel.queue.sync.send', side_effect=RuntimeError('queue unavailable')):
        enqueue_recovery(delivery.id)
    assert PasswordResetDelivery.objects.filter(pk=delivery.id, processed_at__isnull=True).exists()
