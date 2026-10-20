import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=2000)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name", "id"]
        constraints = [models.UniqueConstraint(fields=["restaurant", "id"], name="category_tenant_id_unique")]
        indexes = [models.Index(fields=["restaurant", "is_published", "sort_order"])]


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, max_length=4000)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="BRL")
    is_available = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "id"], name="product_tenant_id_unique"),
            models.CheckConstraint(condition=Q(price__gte=0), name="product_price_nonnegative"),
        ]
        indexes = [models.Index(fields=["restaurant", "is_published", "category"])]


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE, related_name="product_images")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    storage_key = models.CharField(max_length=300, unique=True, editable=False)
    size = models.PositiveIntegerField()
    mime = models.CharField(max_length=40)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["restaurant", "product"])]
