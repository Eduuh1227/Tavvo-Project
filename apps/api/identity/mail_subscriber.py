"""Private Vercel subscriber; Django initializes only when a message is handled."""
import os
from uuid import UUID

from asgiref.sync import sync_to_async
from vercel.queue import subscribe


def deliver(payload):
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    from django.db import close_old_connections
    from .mail_delivery import process_delivery
    close_old_connections()
    try:
        process_delivery(UUID(payload['delivery_id']))
    finally:
        close_old_connections()


@subscribe(topic='tavvo-password-recovery', retry_after=30, max_attempts=5, max_concurrency=2)
async def recover_access(payload: dict[str, str]) -> None:
    await sync_to_async(deliver, thread_sensitive=True)(payload)
