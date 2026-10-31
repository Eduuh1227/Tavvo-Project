from django.core.management.base import BaseCommand
from identity.mail_delivery import process_delivery
from identity.models import PasswordResetDelivery


class Command(BaseCommand):
    help = 'Process a bounded batch of recovery outbox messages, including queue enqueue failures.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        identifiers = list(PasswordResetDelivery.objects.filter(processed_at__isnull=True, attempts__lt=5)
                           .order_by('created_at').values_list('id', flat=True)[:max(0, min(options['limit'], 1000))])
        for identifier in identifiers:
            try:
                process_delivery(identifier)
            except RuntimeError:
                pass
        self.stdout.write(f'Processed {len(identifiers)} recovery mail request(s).')
