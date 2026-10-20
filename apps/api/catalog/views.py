from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record
from restaurants.views import TenantAccessMixin

from . import storage
from .models import Category, Product, ProductImage
from .serializers import AvailabilitySerializer, CategorySerializer, ImageUploadSerializer, ProductImageSerializer, ProductSerializer


class CategoryViewSet(TenantAccessMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Category.objects.none()
        return Category.objects.filter(restaurant=self.restaurant(), archived_at__isnull=True)

    def perform_create(self, serializer):
        restaurant = self.restaurant("manage")
        category = serializer.save(restaurant=restaurant)
        record(self.request, restaurant, "category.created", category)

    def perform_update(self, serializer):
        category = serializer.save()
        record(self.request, self.restaurant("manage"), "category.updated", category, {"is_published": category.is_published})

    def perform_destroy(self, instance):
        instance.archived_at = timezone.now()
        instance.is_published = False
        instance.save(update_fields=["archived_at", "is_published", "updated_at"])
        record(self.request, self.restaurant("manage"), "category.archived", instance)


class ProductViewSet(TenantAccessMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()
        requested_action = "availability" if self.action == "availability" else None
        queryset = Product.objects.filter(restaurant=self.restaurant(requested_action), archived_at__isnull=True).prefetch_related("images")
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            queryset = queryset.select_for_update()
        return queryset

    def get_serializer_context(self):
        if self.action == "availability":
            return {"request": self.request, "restaurant": self.restaurant("availability")}
        return super().get_serializer_context()

    def perform_create(self, serializer):
        restaurant = self.restaurant("manage")
        product = serializer.save(restaurant=restaurant)
        record(self.request, restaurant, "product.created", product)

    def perform_update(self, serializer):
        product = serializer.save(version=serializer.instance.version + 1)
        record(self.request, self.restaurant("manage"), "product.updated", product, {"is_published": product.is_published})

    def perform_destroy(self, instance):
        instance.archived_at = timezone.now()
        instance.is_published = False
        instance.version += 1
        instance.save(update_fields=["archived_at", "is_published", "version", "updated_at"])
        record(self.request, self.restaurant("manage"), "product.archived", instance)

    @extend_schema(request=AvailabilitySerializer, responses=ProductSerializer)
    @action(detail=True, methods=["patch"])
    def availability(self, request, **kwargs):
        product = self.get_object()
        serializer = AvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product.is_available = serializer.validated_data["is_available"]
        product.version += 1
        product.save(update_fields=["is_available", "version", "updated_at"])
        record(request, self.restaurant("availability"), "product.availability_changed", product, {"is_available": product.is_available})
        return Response(ProductSerializer(product, context=self.get_serializer_context()).data)


class ProductImageUploadView(TenantAccessMixin, generics.GenericAPIView):
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ImageUploadSerializer

    @extend_schema(responses={201: ProductImageSerializer})
    def post(self, request, restaurant_id, product_id):
        restaurant = self.restaurant("manage")
        product = get_object_or_404(Product, restaurant=restaurant, pk=product_id, archived_at__isnull=True)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key, size, mime = storage.upload_image(restaurant.pk, product.pk, serializer.validated_data["file"])
        try:
            image = ProductImage.objects.create(restaurant=restaurant, product=product, storage_key=key,
                                                size=size, mime=mime, sort_order=serializer.validated_data["sort_order"])
            record(request, restaurant, "image.created", image)
        except Exception:
            storage.delete_image(key)
            raise
        return Response(ProductImageSerializer(image, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ProductImageDeleteView(TenantAccessMixin, APIView):
    @extend_schema(responses={204: None})
    def delete(self, request, restaurant_id, product_id, image_id):
        restaurant = self.restaurant("manage")
        image = get_object_or_404(ProductImage, pk=image_id, product_id=product_id, restaurant=restaurant)
        record(request, restaurant, "image.deleted", image)
        key = image.storage_key
        image.delete()
        transaction.on_commit(lambda: storage.delete_image(key))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PrivateImageView(TenantAccessMixin, APIView):
    @extend_schema(responses={(200, "image/jpeg"): bytes})
    def get(self, request, restaurant_id, image_id):
        image = get_object_or_404(ProductImage, pk=image_id, restaurant=self.restaurant("read"))
        return storage.image_response(image)
