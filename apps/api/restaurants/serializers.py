import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Restaurant, RestaurantDomain, RestaurantMembership, RestaurantSettings


def normalize_hostname(value):
    value = value.strip().lower().rstrip(".")
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise serializers.ValidationError("Invalid hostname.") from exc
    if len(value) > 253 or "." not in value or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in value.split(".")
    ):
        raise serializers.ValidationError("Use a hostname without protocol, port or path.")
    return value


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ["id", "name", "slug", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_slug(self, value):
        value = value.lower()
        queryset = Restaurant.objects.filter(slug=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("This slug is already in use.")
        return value


@extend_schema_field({"type": "object", "additionalProperties": {"type": "string"}})
class PublicConfigField(serializers.JSONField):
    """JSON input with an allowlisted string dictionary, described in OpenAPI."""


class SettingsSerializer(serializers.ModelSerializer):
    public_config = PublicConfigField(required=False)

    class Meta:
        model = RestaurantSettings
        fields = ["locale", "timezone", "currency", "public_config", "updated_at"]
        read_only_fields = ["updated_at"]

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise serializers.ValidationError("Use a valid IANA timezone.") from exc
        return value

    def validate_locale(self, value):
        if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?", value):
            raise serializers.ValidationError("Use a locale such as pt-BR.")
        return value

    def validate_currency(self, value):
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise serializers.ValidationError("Currency must contain three uppercase letters.")
        return value

    def validate_public_config(self, value):
        allowed = {"description", "address", "phone", "website"}
        if not isinstance(value, dict) or set(value) - allowed:
            raise serializers.ValidationError("Allowed public fields: description, address, phone, website.")
        if any(not isinstance(item, str) or len(item) > 2000 for item in value.values()):
            raise serializers.ValidationError("Public fields must be text of at most 2000 characters.")
        return value


class MembershipSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = RestaurantMembership
        fields = ["id", "user", "email", "name", "role", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        user = attrs.get("user", getattr(self.instance, "user", None))
        restaurant = self.context["restaurant"]
        existing = RestaurantMembership.objects.filter(restaurant=restaurant, user=user)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError({"user": "This user already has a membership; update it instead."})
        return attrs


class DomainSerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(max_length=253)

    class Meta:
        model = RestaurantDomain
        fields = ["id", "hostname", "status", "is_primary", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []

    def validate_hostname(self, value):
        value = normalize_hostname(value)
        existing = RestaurantDomain.objects.filter(hostname=value)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("This hostname is already associated with a restaurant.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if attrs.get("status") == RestaurantDomain.Status.VERIFIED:
            from core.access import require_platform

            require_platform(request)
        if self.instance and "hostname" in attrs and attrs["hostname"] != self.instance.hostname:
            # A verified association does not transfer to a new hostname automatically.
            attrs["status"] = RestaurantDomain.Status.PENDING
        if attrs.get("is_primary"):
            existing = RestaurantDomain.objects.filter(restaurant=self.context["restaurant"], is_primary=True)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({"is_primary": "Unset the current primary domain first."})
        return attrs
