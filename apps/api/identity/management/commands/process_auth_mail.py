from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from identity.models import PasswordResetDelivery, User


class Command(BaseCommand):
    help = "Process a bounded batch of password-recovery mail from PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        count = 0
        for _ in range(options["limit"]):
            with transaction.atomic():
                delivery = PasswordResetDelivery.objects.select_for_update(skip_locked=True).filter(processed_at__isnull=True, attempts__lt=5).order_by("created_at").first()
                if delivery is None:
                    break
                user = User.objects.filter(email__iexact=delivery.email, is_active=True).first()
                try:
                    if user and user.has_usable_password() and delivery.created_at > timezone.now() - timedelta(minutes=15):
                        params = urlencode({"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": default_token_generator.make_token(user)})
                        url = f"{settings.TAVVO_PASSWORD_RESET_URL}?{params}"
                        send_mail("Recuperação de acesso — Tavvo", f"Para redefinir sua senha, acesse:\n\n{url}\n\nSe não solicitou esta alteração, ignore esta mensagem.", settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                    delivery.processed_at = timezone.now()
                except Exception:
                    # Do not log SMTP exceptions, destinations or recovery tokens.
                    delivery.attempts += 1
                delivery.save(update_fields=["processed_at", "attempts"])
                count += 1
        self.stdout.write(f"Processed {count} recovery mail request(s).")
