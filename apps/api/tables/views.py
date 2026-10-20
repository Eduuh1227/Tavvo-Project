import io
import re
import uuid

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from audit.services import record
from core.tenancy import set_tenant
from publishing.views import PublicView
from restaurants.models import Restaurant
from restaurants.views import TenantAccessMixin

from .models import MenuTable
from .serializers import MenuTableSerializer, QRResolutionSerializer


class MenuTableViewSet(TenantAccessMixin, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = MenuTableSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return MenuTable.objects.none()
        return MenuTable.objects.filter(restaurant=self.restaurant())

    def perform_create(self, serializer):
        restaurant = self.restaurant("manage")
        table = serializer.save(restaurant=restaurant)
        record(self.request, restaurant, "table.created", table)

    def perform_update(self, serializer):
        table = serializer.save()
        record(self.request, self.restaurant("manage"), "table.updated", table, {"status": table.status})

    @extend_schema(parameters=[OpenApiParameter("format", str, enum=["svg", "png"])],
                   responses={(200, "image/svg+xml"): bytes, (200, "image/png"): bytes})
    @action(detail=True, methods=["get"])
    def qr(self, request, **kwargs):
        table = self.get_object()
        output_format = request.query_params.get("format", "svg")
        if output_format not in ("svg", "png"):
            raise ValidationError({"format": "Use svg or png."})
        url = MenuTableSerializer(table).get_public_url(table)
        factory = qrcode.image.svg.SvgPathImage if output_format == "svg" else None
        qr = qrcode.make(url, image_factory=factory, box_size=8, border=4)
        output = io.BytesIO()
        qr.save(output)
        response = HttpResponse(output.getvalue(), content_type="image/svg+xml" if output_format == "svg" else "image/png")
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class QRResolverView(PublicView):
    @extend_schema(responses=QRResolutionSerializer)
    def get(self, request, code):
        if not re.fullmatch(r"[0-9a-f]{32}\.[A-Za-z0-9_-]{32}", code):
            raise NotFound()
        restaurant_id = uuid.UUID(hex=code.split(".", 1)[0])
        restaurant = get_object_or_404(Restaurant, pk=restaurant_id, status=Restaurant.Status.ACTIVE)
        set_tenant(restaurant.pk)
        table = get_object_or_404(MenuTable, restaurant=restaurant, public_code=code, status=MenuTable.Status.ACTIVE)
        return Response({
            "restaurant": {"id": str(restaurant.pk), "name": restaurant.name, "slug": restaurant.slug},
            "table": {"label": table.label, "public_code": table.public_code},
            "menu_url": f"{settings.PUBLIC_SITE_URL.rstrip('/')}/r/{restaurant.slug}",
        })
