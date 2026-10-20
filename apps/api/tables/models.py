import secrets
import uuid

from django.db import models


class MenuTable(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE, related_name="tables")
    label = models.CharField(max_length=80)
    public_code = models.CharField(max_length=90, unique=True, editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["label", "id"]
        constraints = [models.UniqueConstraint(fields=["restaurant", "label"], name="table_restaurant_label_unique")]

    def save(self, *args, **kwargs):
        if not self.public_code:
            # Tenant UUID is a routing hint only; the random suffix authorizes no private data.
            self.public_code = f"{self.restaurant_id.hex}.{secrets.token_urlsafe(24)}"
        super().save(*args, **kwargs)
