from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Category, Product, ProductImage
from catalog.storage import image_response

from .serializers import DomainQuerySerializer, PublicMenuSerializer, PublicRestaurantSerializer
from .services import public_restaurant, resolve_domain


class PublicView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class PublicRestaurantView(PublicView):
    @extend_schema(responses=PublicRestaurantSerializer)
    def get(self, request, slug):
        restaurant = public_restaurant(slug, request)
        return Response(PublicRestaurantSerializer(restaurant).data)


class PublicMenuView(PublicView):
    @extend_schema(responses=PublicMenuSerializer)
    def get(self, request, slug):
        restaurant = public_restaurant(slug, request)
        products = Product.objects.filter(restaurant=restaurant, is_published=True, archived_at__isnull=True).prefetch_related("images")
        categories = Category.objects.filter(restaurant=restaurant, is_published=True, archived_at__isnull=True).prefetch_related(
            Prefetch("products", queryset=products, to_attr="published_products")
        )
        serializer = PublicMenuSerializer({"restaurant": restaurant, "categories": categories},
                                          context={"request": request, "public_slug": restaurant.slug})
        return Response(serializer.data)


class DomainResolverView(PublicView):
    @extend_schema(parameters=[DomainQuerySerializer], responses=PublicRestaurantSerializer)
    def get(self, request):
        query = DomainQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        restaurant = resolve_domain(query.validated_data["hostname"])
        return Response(PublicRestaurantSerializer(restaurant).data)


class PublicImageView(PublicView):
    @extend_schema(responses={(200, "image/jpeg"): bytes})
    def get(self, request, slug, image_id):
        restaurant = public_restaurant(slug, request)
        image = get_object_or_404(
            ProductImage, pk=image_id, restaurant=restaurant,
            product__restaurant=restaurant, product__is_published=True, product__archived_at__isnull=True,
            product__category__restaurant=restaurant, product__category__is_published=True,
            product__category__archived_at__isnull=True,
        )
        return image_response(image)
