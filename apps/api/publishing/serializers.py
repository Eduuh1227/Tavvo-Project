from rest_framework import serializers

from catalog.models import Product
from catalog.serializers import ProductImageSerializer
from restaurants.models import Restaurant
from restaurants.serializers import SettingsSerializer


class PublicRestaurantSerializer(serializers.ModelSerializer):
    settings = SettingsSerializer(read_only=True)

    class Meta:
        model = Restaurant
        fields = ["id", "name", "slug", "settings"]
        read_only_fields = fields


class PublicProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "currency", "is_available", "images"]
        read_only_fields = fields


class PublicCategorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    sort_order = serializers.IntegerField()
    products = PublicProductSerializer(many=True, read_only=True, source="published_products")


class PublicMenuSerializer(serializers.Serializer):
    restaurant = PublicRestaurantSerializer()
    categories = PublicCategorySerializer(many=True)


class DomainQuerySerializer(serializers.Serializer):
    hostname = serializers.CharField(max_length=253)
