import io

import boto3
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from moto import mock_aws
from PIL import Image
from rest_framework.test import APIClient

from audit.models import AuditLog
from catalog.models import Category, Product, ProductImage
from core.tenancy import set_tenant
from identity.models import User
from restaurants.models import Restaurant, RestaurantDomain, RestaurantMembership, RestaurantSettings

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenants():
    a = Restaurant.objects.create(name="Restaurante A", slug="restaurante-a")
    b = Restaurant.objects.create(name="Restaurante B", slug="restaurante-b")
    manager_a = User.objects.create_user(email="manager-a@example.test", password="Secure-Password-A1!", name="Manager A")
    manager_b = User.objects.create_user(email="manager-b@example.test", password="Secure-Password-B1!", name="Manager B")
    staff = User.objects.create_user(email="staff@example.test", password="Secure-Password-S1!", name="Staff")
    RestaurantMembership.objects.create(restaurant=a, user=manager_a, role="manager")
    RestaurantMembership.objects.create(restaurant=b, user=manager_b, role="manager")
    RestaurantMembership.objects.create(restaurant=a, user=staff, role="staff")
    set_tenant(a.pk)
    RestaurantSettings.objects.create(restaurant=a)
    category_a = Category.objects.create(restaurant=a, name="A published category", is_published=True)
    product_a = Product.objects.create(restaurant=a, category=category_a, name="A product", price="12.50", is_published=True)
    set_tenant(b.pk)
    RestaurantSettings.objects.create(restaurant=b)
    category_b = Category.objects.create(restaurant=b, name="B published category", is_published=True)
    product_b = Product.objects.create(restaurant=b, category=category_b, name="B product", price="21.90", is_published=True)
    return {"a": a, "b": b, "manager_a": manager_a, "manager_b": manager_b, "staff": staff,
            "category_a": category_a, "category_b": category_b, "product_a": product_a, "product_b": product_b}


def authenticated(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_category_product_publication_persists_and_hides_immediately(tenants):
    client = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}'
    category = client.post(f"{prefix}/categories/", {"name": "Desserts", "is_published": True}, format="json")
    assert category.status_code == 201, category.data
    product = client.post(f"{prefix}/products/", {"category": category.data["id"], "name": "Cake", "price": "15.25", "is_published": True}, format="json")
    assert product.status_code == 201, product.data
    set_tenant(tenants["a"].pk)
    assert str(Product.objects.get(pk=product.data["id"]).price) == "15.25"
    public = APIClient()
    menu = public.get("/v1/public/restaurants/restaurante-a/menu/")
    assert menu.status_code == 200
    names = [p["name"] for c in menu.data["categories"] for p in c["products"]]
    assert "Cake" in names and "B product" not in names
    assert menu["Cache-Control"] == "no-store"
    hidden = client.patch(f'{prefix}/products/{product.data["id"]}/', {"is_published": False}, format="json")
    assert hidden.status_code == 200
    menu = public.get("/v1/public/restaurants/restaurante-a/menu/")
    assert "Cake" not in [p["name"] for c in menu.data["categories"] for p in c["products"]]
    set_tenant(tenants["a"].pk)
    assert AuditLog.objects.filter(action="product.updated", resource_id=product.data["id"]).exists()


def test_url_tampering_and_foreign_associations_are_denied(tenants):
    client = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}'
    foreign_prefix = f'/v1/restaurants/{tenants["b"].pk}'
    assert client.get(f"{foreign_prefix}/products/").status_code == 404
    assert client.patch(f'{foreign_prefix}/products/{tenants["product_b"].pk}/', {"name": "stolen"}, format="json").status_code == 404
    assert client.get(f'{prefix}/products/{tenants["product_b"].pk}/').status_code == 404
    cross_category = client.patch(f'{prefix}/products/{tenants["product_a"].pk}/', {"category": str(tenants["category_b"].pk)}, format="json")
    assert cross_category.status_code == 400
    create = client.post(f"{prefix}/products/", {"name": "cross", "price": "1.00", "category": str(tenants["category_b"].pk)}, format="json")
    assert create.status_code == 400


def test_staff_can_change_availability_but_not_price_or_settings(tenants):
    client = authenticated(tenants["staff"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}'
    product_url = f'{prefix}/products/{tenants["product_a"].pk}'
    assert client.get(f"{prefix}/products/").status_code == 200
    result = client.patch(f"{product_url}/availability/", {"is_available": False}, format="json")
    assert result.status_code == 200, result.data
    assert result.data["is_available"] is False
    assert client.patch(f"{product_url}/", {"price": "0.00"}, format="json").status_code == 403
    assert client.get(f"{prefix}/settings/").status_code == 403
    assert client.get(f"{prefix}/audit/").status_code == 403
    assert client.post(f"{prefix}/categories/", {"name": "unauthorized"}, format="json").status_code == 403
    public = APIClient().get("/v1/public/restaurants/restaurante-a/menu/")
    assert public.data["categories"][0]["products"][0]["is_available"] is False


def test_revoked_membership_is_rechecked_on_every_request(tenants):
    client = authenticated(tenants["manager_a"])
    url = f'/v1/restaurants/{tenants["a"].pk}/products/'
    assert client.get(url).status_code == 200
    RestaurantMembership.objects.filter(restaurant=tenants["a"], user=tenants["manager_a"]).update(status="revoked")
    assert client.get(url).status_code == 404


def test_archiving_parent_hides_published_products(tenants):
    client = authenticated(tenants["manager_a"])
    category_url = f'/v1/restaurants/{tenants["a"].pk}/categories/{tenants["category_a"].pk}/'
    assert client.delete(category_url).status_code == 204
    menu = APIClient().get("/v1/public/restaurants/restaurante-a/menu/")
    assert menu.data["categories"] == []
    set_tenant(tenants["a"].pk)
    assert Product.objects.filter(pk=tenants["product_a"].pk).exists()
    assert Category.objects.get(pk=tenants["category_a"].pk).archived_at is not None


def test_domain_resolver_has_no_fallback_and_cannot_cross_tenants(tenants):
    RestaurantDomain.objects.create(restaurant=tenants["a"], hostname="A.Example.Test", status="verified")
    public = APIClient()
    result = public.get("/v1/public/resolve/", {"hostname": "a.example.test"})
    assert result.status_code == 200
    assert result.data["slug"] == "restaurante-a"
    assert public.get("/v1/public/resolve/", {"hostname": "unknown.example.test"}).status_code == 404
    assert public.get("/v1/public/restaurants/restaurante-b/menu/", {"hostname": "a.example.test"}).status_code == 404
    assert public.get("/v1/public/resolve/", {"hostname": "https://a.example.test/path"}).status_code == 400
    manager = authenticated(tenants["manager_a"])
    assert manager.post(f'/v1/restaurants/{tenants["a"].pk}/domains/', {"hostname": "evil.example.test", "status": "verified"}, format="json").status_code == 403


def test_qr_code_is_stable_and_respects_table_and_restaurant_status(tenants):
    manager = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}/tables'
    table = manager.post(f"{prefix}/", {"label": "05"}, format="json")
    assert table.status_code == 201, table.data
    code = table.data["public_code"]
    assert len(code.split(".")[1]) == 32
    for extension, mime in [("svg", "image/svg+xml"), ("png", "image/png")]:
        qr = manager.get(f'{prefix}/{table.data["id"]}/qr/', {"format": extension})
        assert qr.status_code == 200, getattr(qr, "data", None)
        assert qr["Content-Type"] == mime
        assert len(qr.content) > 100
    public = APIClient()
    resolution = public.get(f"/v1/public/qr/{code}/")
    assert resolution.status_code == 200
    assert resolution.data["restaurant"]["slug"] == "restaurante-a"
    assert resolution.data["table"]["label"] == "05"
    edited = manager.patch(f'{prefix}/{table.data["id"]}/', {"label": "06"}, format="json")
    assert edited.data["public_code"] == code
    manager.patch(f'{prefix}/{table.data["id"]}/', {"status": "inactive"}, format="json")
    assert public.get(f"/v1/public/qr/{code}/").status_code == 404
    assert public.get("/v1/public/qr/not-a-code/").status_code == 404


def png_file():
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile("photo.png", buffer.getvalue(), content_type="image/png")


def test_s3_contract_and_image_visibility_follow_publication(tenants, settings, django_capture_on_commit_callbacks):
    settings.S3_ENDPOINT_URL = None
    settings.S3_ACCESS_KEY = "testing"
    settings.S3_SECRET_KEY = "testing"
    settings.S3_REGION = "us-east-1"
    settings.S3_BUCKET = "tavvo-test-images"
    manager = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}/products/{tenants["product_a"].pk}'
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing")
        s3.create_bucket(Bucket=settings.S3_BUCKET)
        response = manager.post(f"{prefix}/images/", {"file": png_file()}, format="multipart")
        assert response.status_code == 201, response.data
        image_id = response.data["id"]
        set_tenant(tenants["a"].pk)
        image = ProductImage.objects.get(pk=image_id)
        assert s3.head_object(Bucket=settings.S3_BUCKET, Key=image.storage_key)["ContentType"] == "image/png"
        public = APIClient()
        url = f'/v1/public/restaurants/restaurante-a/images/{image_id}/'
        served = public.get(url)
        assert served.status_code == 200
        assert b"".join(served.streaming_content).startswith(b"\x89PNG")
        assert public.get(f'/v1/public/restaurants/restaurante-b/images/{image_id}/').status_code == 404
        assert authenticated(tenants["manager_b"]).get(f'/v1/restaurants/{tenants["a"].pk}/images/{image_id}/').status_code == 404
        manager.patch(f"{prefix}/", {"is_published": False}, format="json")
        assert public.get(url).status_code == 404
        with django_capture_on_commit_callbacks(execute=True):
            assert manager.delete(f"{prefix}/images/{image_id}/").status_code == 204
        assert s3.list_objects_v2(Bucket=settings.S3_BUCKET).get("KeyCount") == 0


def test_image_upload_rejects_fake_content_and_size_without_storage_call(tenants, monkeypatch):
    from catalog import storage

    monkeypatch.setattr(storage, "client", lambda: pytest.fail("Invalid upload must not reach storage"))
    manager = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}/products/{tenants["product_a"].pk}/images/'
    fake = SimpleUploadedFile("photo.jpg", b"<script>bad file</script>", content_type="image/jpeg")
    assert manager.post(prefix, {"file": fake}, format="multipart").status_code == 400
    oversized = SimpleUploadedFile("large.jpg", b"a" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
    assert manager.post(prefix, {"file": oversized}, format="multipart").status_code == 400


def test_inactive_restaurant_disappears_from_every_public_resolver(tenants):
    RestaurantDomain.objects.create(restaurant=tenants["a"], hostname="a.example.test", status="verified")
    manager = authenticated(tenants["manager_a"])
    table = manager.post(f'/v1/restaurants/{tenants["a"].pk}/tables/', {"label": "02"}, format="json")
    Restaurant.objects.filter(pk=tenants["a"].pk).update(status="inactive")
    public = APIClient()
    assert public.get("/v1/public/restaurants/restaurante-a/").status_code == 404
    assert public.get("/v1/public/restaurants/restaurante-a/menu/").status_code == 404
    assert public.get("/v1/public/resolve/", {"hostname": "a.example.test"}).status_code == 404
    assert public.get(f'/v1/public/qr/{table.data["public_code"]}/').status_code == 404


def test_platform_requires_mfa_and_manages_membership_revocation(tenants):
    platform_user = User.objects.create_user(email="platform@example.test", password="Platform-Password-A1!", name="Tavvo", is_platform_admin=True)
    platform = authenticated(platform_user)
    assert platform.get("/v1/platform/restaurants/").status_code == 403
    session = platform.session
    session["mfa_verified"] = True
    session.save()
    created = platform.post("/v1/platform/restaurants/", {"name": "Restaurant C", "slug": "restaurant-c"}, format="json")
    assert created.status_code == 201, created.data
    tenant_id = created.data["id"]
    membership = platform.post(f"/v1/platform/restaurants/{tenant_id}/memberships/", {"user": str(tenants["manager_a"].pk), "role": "manager"}, format="json")
    assert membership.status_code == 201, membership.data
    member = authenticated(tenants["manager_a"])
    assert member.get(f"/v1/restaurants/{tenant_id}/products/").status_code == 200
    revoked = platform.patch(f'/v1/platform/restaurants/{tenant_id}/memberships/{membership.data["id"]}/', {"status": "revoked"}, format="json")
    assert revoked.status_code == 200, revoked.data
    assert member.get(f"/v1/restaurants/{tenant_id}/products/").status_code == 404
    assert member.get("/v1/platform/restaurants/").status_code == 403
    audit = platform.get(f"/v1/restaurants/{tenant_id}/audit/")
    assert audit.status_code == 200
    assert {"restaurant.created", "membership.created", "membership.updated"}.issubset({item["action"] for item in audit.data["results"]})
    assert platform.delete(f"/v1/restaurants/{tenant_id}/audit/").status_code == 405


def test_platform_domain_verification_is_normalized_and_new_hostname_is_pending(tenants):
    admin = User.objects.create_user(email="domains@example.test", password="Platform-Password-A1!", name="Tavvo", is_platform_admin=True)
    platform = authenticated(admin)
    session = platform.session
    session["mfa_verified"] = True
    session.save()
    prefix = f'/v1/restaurants/{tenants["a"].pk}/domains'
    created = platform.post(f"{prefix}/", {"hostname": "A.Example.Test.", "status": "verified", "is_primary": True}, format="json")
    assert created.status_code == 201, created.data
    assert created.data["hostname"] == "a.example.test"
    duplicate = platform.post(f'/v1/restaurants/{tenants["b"].pk}/domains/', {"hostname": "A.EXAMPLE.TEST"}, format="json")
    assert duplicate.status_code == 400
    changed = platform.patch(f'{prefix}/{created.data["id"]}/', {"hostname": "new.example.test"}, format="json")
    assert changed.status_code == 200
    assert changed.data["status"] == "pending"
    assert APIClient().get("/v1/public/resolve/", {"hostname": "new.example.test"}).status_code == 404


def test_settings_are_validated_and_public_payload_is_allowlisted(tenants):
    manager = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}/settings/'
    assert manager.patch(prefix, {"public_config": {"password": "sensitive"}}, format="json").status_code == 400
    assert manager.patch(prefix, {"timezone": "invalid-zone"}, format="json").status_code == 400
    assert manager.patch(prefix, {"currency": "wrong"}, format="json").status_code == 400
    result = manager.patch(prefix, {"public_config": {"description": "Our real menu", "phone": "123"}}, format="json")
    assert result.status_code == 200
    public = APIClient().get("/v1/public/restaurants/restaurante-a/")
    assert public.data["settings"]["public_config"]["description"] == "Our real menu"
    assert "memberships" not in public.data
    assert "status" not in public.data


def test_currency_is_exact_and_unpublished_category_cannot_leak_products(tenants):
    manager = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}'
    product_url = f'{prefix}/products/{tenants["product_a"].pk}/'
    assert manager.patch(product_url, {"price": "-0.01"}, format="json").status_code == 400
    assert manager.patch(product_url, {"price": "12.345"}, format="json").status_code == 400
    result = manager.patch(product_url, {"price": "0.10"}, format="json")
    assert result.status_code == 200
    assert result.data["price"] == "0.10"
    manager.patch(f'{prefix}/categories/{tenants["category_a"].pk}/', {"is_published": False}, format="json")
    assert APIClient().get("/v1/public/restaurants/restaurante-a/menu/").data["categories"] == []


def test_empty_or_unverified_explicit_hostname_never_falls_back_to_slug(tenants):
    RestaurantDomain.objects.create(restaurant=tenants["a"], hostname="pending.example.test", status="pending")
    public = APIClient()
    url = "/v1/public/restaurants/restaurante-a/menu/"
    assert public.get(url, {"hostname": ""}).status_code == 400
    assert public.get(url, {"hostname": "pending.example.test"}).status_code == 404
    assert public.get(url, {"hostname": "missing.example.test"}).status_code == 404


def test_audit_failure_rolls_back_catalog_mutation(tenants, monkeypatch):
    from catalog import views
    from rest_framework.exceptions import ValidationError

    def failing_audit(*args, **kwargs):
        raise ValidationError("Audit write failed")

    monkeypatch.setattr(views, "record", failing_audit)
    manager = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}'
    response = manager.patch(f'{prefix}/products/{tenants["product_a"].pk}/', {"price": "99.99"}, format="json")
    assert response.status_code == 400
    set_tenant(tenants["a"].pk)
    tenants["product_a"].refresh_from_db()
    assert str(tenants["product_a"].price) == "12.50"


def test_payload_cannot_transfer_tenant_or_escalate_staff_permissions(tenants):
    manager = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}'
    product_url = f'{prefix}/products/{tenants["product_a"].pk}'
    response = manager.patch(f"{product_url}/", {"restaurant": str(tenants["b"].pk), "version": 999,
                                               "storage_key": "foreign/private.png"}, format="json")
    assert response.status_code == 200
    set_tenant(tenants["a"].pk)
    tenants["product_a"].refresh_from_db()
    assert tenants["product_a"].restaurant_id == tenants["a"].pk
    assert tenants["product_a"].version == 2
    staff = authenticated(tenants["staff"])
    response = staff.patch(f"{product_url}/availability/", {"is_available": False, "price": "0.01",
                                                          "is_published": False}, format="json")
    assert response.status_code == 200
    set_tenant(tenants["a"].pk)
    tenants["product_a"].refresh_from_db()
    assert str(tenants["product_a"].price) == "12.50"
    assert tenants["product_a"].is_published is True
    assert staff.delete(f"{product_url}/").status_code == 403
    assert staff.patch(f'{prefix}/categories/{tenants["category_a"].pk}/', {"is_published": False}, format="json").status_code == 403
    assert staff.post(f"{prefix}/tables/", {"label": "unauthorized"}, format="json").status_code == 403
    assert staff.get(f"{prefix}/domains/").status_code == 403
    assert staff.post(f'/v1/platform/restaurants/{tenants["a"].pk}/memberships/',
                      {"user": str(tenants["staff"].pk), "role": "manager"}, format="json").status_code == 403


def test_unauthorized_image_mutation_never_reaches_storage(tenants, monkeypatch):
    from catalog import storage

    monkeypatch.setattr(storage, "client", lambda: pytest.fail("Denied upload must not reach storage"))
    prefix = f'/v1/restaurants/{tenants["a"].pk}/products/{tenants["product_a"].pk}/images/'
    assert authenticated(tenants["staff"]).post(prefix, {"file": png_file()}, format="multipart").status_code == 403
    assert authenticated(tenants["manager_b"]).post(prefix, {"file": png_file()}, format="multipart").status_code == 404


def test_inactive_restaurant_immediately_blocks_member_access(tenants):
    manager = authenticated(tenants["manager_a"])
    prefix = f'/v1/restaurants/{tenants["a"].pk}'
    assert manager.get(f"{prefix}/products/").status_code == 200
    Restaurant.objects.filter(pk=tenants["a"].pk).update(status="inactive")
    assert manager.get(f"{prefix}/products/").status_code == 403
    assert manager.patch(f'{prefix}/products/{tenants["product_a"].pk}/', {"price": "1.00"}, format="json").status_code == 403
