import re

from rest_framework import serializers
from django.urls import reverse

from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "sort_order", "is_published", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "sort_order", "size", "mime"]
        read_only_fields = fields

    def get_url(self, image) -> str:
        request = self.context.get("request")
        public_slug = self.context.get("public_slug")
        if public_slug:
            url = reverse("public-image", kwargs={"slug": public_slug, "image_id": image.pk})
        else:
            url = reverse("private-image", kwargs={"restaurant_id": image.restaurant_id, "image_id": image.pk})
        return request.build_absolute_uri(url) if request else url


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none())
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "category", "name", "description", "price", "currency", "is_available", "is_published",
                  "sort_order", "version", "images", "created_at", "updated_at"]
        read_only_fields = ["id", "version", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        restaurant = self.context.get("restaurant")
        if restaurant:
            self.fields["category"].queryset = Category.objects.filter(restaurant=restaurant, archived_at__isnull=True)

    def validate_currency(self, value):
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise serializers.ValidationError("Currency must contain three uppercase letters.")
        return value


class AvailabilitySerializer(serializers.Serializer):
    is_available = serializers.BooleanField()


class ImageUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    sort_order = serializers.IntegerField(min_value=0, default=0)
