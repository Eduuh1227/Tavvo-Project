from django.conf import settings
from rest_framework import serializers
from identity.schema import RestaurantSummary

from .models import MenuTable


class MenuTableSerializer(serializers.ModelSerializer):
    public_url = serializers.SerializerMethodField()

    class Meta:
        model = MenuTable
        fields = ["id", "label", "status", "public_code", "public_url", "created_at", "updated_at"]
        read_only_fields = ["id", "public_code", "public_url", "created_at", "updated_at"]
        validators = []

    def get_public_url(self, table) -> str:
        return f"{settings.PUBLIC_SITE_URL.rstrip('/')}/q/{table.public_code}"

    def validate_label(self, value):
        existing = MenuTable.objects.filter(restaurant=self.context["restaurant"], label=value)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("A table with this label already exists.")
        return value


class PublicTableSerializer(serializers.Serializer):
    label = serializers.CharField()
    public_code = serializers.CharField()


class QRResolutionSerializer(serializers.Serializer):
    restaurant = RestaurantSummary()
    table = PublicTableSerializer()
    menu_url = serializers.URLField()
