import uuid
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalog.models import ProductImage
from catalog.storage import client
from core.tenancy import set_tenant
from restaurants.models import Restaurant


class Command(BaseCommand):
    help = "List private image orphans older than 24 hours; --delete removes only the listed tenant's orphan objects."

    def add_arguments(self, parser):
        parser.add_argument("--restaurant-id", required=True, type=uuid.UUID)
        parser.add_argument("--delete", action="store_true")

    def handle(self, *args, **options):
        restaurant_id = options["restaurant_id"]
        if not Restaurant.objects.filter(pk=restaurant_id).exists():
            raise CommandError("Restaurant does not exist.")
        s3 = client()
        prefix = f"restaurants/{restaurant_id}/"
        cutoff = timezone.now() - timedelta(hours=24)
        count = 0
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=settings.S3_BUCKET, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item["Key"]
                if not key.startswith(prefix) or item["LastModified"] >= cutoff:
                    continue
                with transaction.atomic():
                    set_tenant(restaurant_id)
                    if ProductImage.objects.filter(restaurant_id=restaurant_id, storage_key=key).exists():
                        continue
                    if options["delete"]:
                        s3.delete_object(Bucket=settings.S3_BUCKET, Key=key)
                count += 1
                self.stdout.write(f"{'deleted' if options['delete'] else 'orphan'} {key}")
        self.stdout.write(self.style.SUCCESS(f"{count} orphan object(s) {'deleted' if options['delete'] else 'found; dry run only'}."))
