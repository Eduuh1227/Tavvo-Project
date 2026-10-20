from rest_framework import generics, serializers

from restaurants.views import TenantAccessMixin

from .models import AuditLog


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "actor_user", "action", "resource_type", "resource_id", "metadata", "request_id", "created_at"]
        read_only_fields = fields


class AuditListView(TenantAccessMixin, generics.ListAPIView):
    serializer_class = AuditSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AuditLog.objects.none()
        return AuditLog.objects.filter(restaurant=self.restaurant("audit"))
