from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PasswordResetDelivery, TotpDevice, User
from . import schema
from .security import enrollment_details, issue_recovery_codes, limits_allow, verify_mfa, verify_totp_locked


def error(code, message, status=400):
    return Response({"code": code, "message": message}, status=status)


def csrf_failure(request, reason=""):
    return JsonResponse({"code": "csrf_failed", "message": "Atualize a página e tente novamente."}, status=403)


def audit(request, action, user, metadata=None):
    from audit.services import record
    record(request, None, action, user, metadata)


def memberships_payload(user):
    from restaurants.models import RestaurantMembership
    return [
        {"restaurant": {"id": str(row.restaurant_id), "name": row.restaurant.name, "slug": row.restaurant.slug}, "role": row.role}
        for row in RestaurantMembership.objects.filter(user=user, status="active").select_related("restaurant")
    ]


def user_payload(user, include_memberships=True):
    result = {
        "id": str(user.id), "email": user.email, "name": user.name,
        "is_platform_admin": user.is_platform_admin, "is_active": user.is_active,
        "mfa_enabled": TotpDevice.objects.filter(user=user, confirmed=True).exists(),
    }
    if include_memberships:
        result["memberships"] = memberships_payload(user)
    return result


def begin_session(request, user, mfa_verified=False):
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    now = int(timezone.now().timestamp())
    request.session.update({"auth_started_at": now, "auth_seen_at": now, "auth_version": user.session_version, "mfa_verified": mfa_verified})
    request.session.set_expiry(getattr(settings, "TAVVO_SESSION_ABSOLUTE_SECONDS", 43200))


@method_decorator(csrf_protect, name="dispatch")
class CsrfAPIView(APIView):
    permission_classes = [IsAuthenticated]


class CsrfView(CsrfAPIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=schema.CsrfResult)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginInput(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=1024, trim_whitespace=False)
    otp = serializers.CharField(max_length=64, required=False, allow_blank=True)


class LoginView(CsrfAPIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginInput, responses=PolymorphicProxySerializer(
        component_name="LoginResult", serializers=[schema.IdentityUser, schema.MfaChallenge, schema.MfaSetupRequired], resource_type_field_name=None,
    ))
    def post(self, request):
        values = LoginInput(data=request.data)
        values.is_valid(raise_exception=True)
        data = values.validated_data
        email = data["email"].strip().lower()
        if not limits_allow(request, "login", email):
            return error("rate_limited", "Aguarde antes de tentar novamente.", 429)
        user = authenticate(request, email=email, password=data["password"])
        if user is None:
            return error("invalid_credentials", "E-mail ou senha inválidos.", 401)
        enabled = TotpDevice.objects.filter(user=user, confirmed=True).exists()
        if enabled:
            if not data.get("otp"):
                return Response({"mfa_required": True})
            if not limits_allow(request, "mfa", str(user.id)):
                return error("rate_limited", "Aguarde antes de tentar novamente.", 429)
            if not verify_mfa(user, data["otp"]):
                return error("invalid_otp", "Código de verificação inválido ou já utilizado.", 401)
        begin_session(request, user, mfa_verified=enabled)
        audit(request, "auth.login", user)
        if user.is_platform_admin and not enabled:
            return Response({"mfa_enrollment_required": True})
        return Response(user_payload(user))


class LogoutView(CsrfAPIView):
    permission_classes = [AllowAny]

    @extend_schema(request=schema.EmptyInput, responses={204: None})
    def post(self, request):
        if request.user.is_authenticated:
            audit(request, "auth.logout", request.user)
        logout(request)
        return Response(status=204)


class MeView(CsrfAPIView):
    @extend_schema(responses=schema.IdentityUser)
    def get(self, request):
        return Response(user_payload(request.user))


class MyRestaurantsView(CsrfAPIView):
    @extend_schema(responses=schema.MembershipSummary(many=True))
    def get(self, request):
        return Response(memberships_payload(request.user))


class ResetRequestInput(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class PasswordResetRequestView(CsrfAPIView):
    permission_classes = [AllowAny]

    @extend_schema(request=ResetRequestInput, responses={202: schema.MessageResult})
    def post(self, request):
        values = ResetRequestInput(data=request.data)
        values.is_valid(raise_exception=True)
        email = values.validated_data["email"].lower()
        # Identical response and persistent operation for existing/nonexisting accounts.
        if limits_allow(request, "reset", email):
            PasswordResetDelivery.objects.create(email=email)
        return Response({"message": "Se a conta existir, enviaremos as instruções de recuperação."}, status=202)


class ResetConfirmInput(serializers.Serializer):
    uid = serializers.CharField(max_length=128)
    token = serializers.CharField(max_length=128)
    password = serializers.CharField(max_length=1024, trim_whitespace=False)


class PasswordResetConfirmView(CsrfAPIView):
    permission_classes = [AllowAny]

    @extend_schema(request=ResetConfirmInput, responses={204: None})
    def post(self, request):
        values = ResetConfirmInput(data=request.data)
        values.is_valid(raise_exception=True)
        data = values.validated_data
        if not limits_allow(request, "reset-confirm", data["uid"]):
            return error("rate_limited", "Aguarde antes de tentar novamente.", 429)
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            with transaction.atomic():
                user = User.objects.select_for_update().get(id=uid, is_active=True)
                if not default_token_generator.check_token(user, data["token"]):
                    return error("invalid_reset_token", "Link inválido ou expirado.")
                try:
                    validate_password(data["password"], user=user)
                except DjangoValidationError as exc:
                    # Return a validation response without rolling back the counters
                    # consumed earlier in this request's ATOMIC_REQUESTS transaction.
                    return Response({"code": "invalid_password", "message": "Revise a senha enviada.",
                                     "errors": {"password": exc.messages}}, status=400)
                user.set_password(data["password"])
                user.session_version += 1
                user.save(update_fields=["password", "session_version"])
                audit(request, "auth.password_reset", user)
        except (ValueError, TypeError, UnicodeError, User.DoesNotExist, DjangoValidationError):
            return error("invalid_reset_token", "Link inválido ou expirado.")
        logout(request)
        return Response(status=204)


def recent_login(request):
    return int(timezone.now().timestamp()) - request.session.get("auth_started_at", 0) <= 600


class MfaEnrollView(CsrfAPIView):
    @extend_schema(request=schema.EmptyInput, responses=schema.MfaEnrollment)
    def post(self, request):
        if not recent_login(request):
            return error("reauthentication_required", "Entre novamente para configurar o segundo fator.", 403)
        if not limits_allow(request, "mfa-enroll", str(request.user.id)):
            return error("rate_limited", "Aguarde antes de tentar novamente.", 429)
        details = enrollment_details(request.user)
        if details is None:
            return error("mfa_already_enabled", "Segundo fator já configurado.", 409)
        return Response(details)


class OtpInput(serializers.Serializer):
    otp = serializers.CharField(max_length=64)


class MfaConfirmView(CsrfAPIView):
    @extend_schema(request=OtpInput, responses=schema.MfaConfirmation)
    def post(self, request):
        values = OtpInput(data=request.data)
        values.is_valid(raise_exception=True)
        if not recent_login(request):
            return error("reauthentication_required", "Entre novamente para configurar o segundo fator.", 403)
        if not limits_allow(request, "mfa", str(request.user.id)):
            return error("rate_limited", "Aguarde antes de tentar novamente.", 429)
        with transaction.atomic():
            device = TotpDevice.objects.select_for_update().filter(user=request.user, confirmed=False).first()
            if device is None or not verify_totp_locked(device, values.validated_data["otp"]):
                return error("invalid_otp", "Código inválido ou configuração já concluída.", 400)
            device.confirmed = True
            device.save(update_fields=["confirmed"])
            codes = issue_recovery_codes(request.user)
            # Sessions opened before enrollment have not proved possession of MFA.
            # Invalidate all of them and retain only this newly verified session.
            User.objects.filter(pk=request.user.pk).update(session_version=F("session_version") + 1)
            request.user.refresh_from_db(fields=["session_version"])
            audit(request, "auth.mfa_enabled", request.user)
        request.session.cycle_key()
        request.session["auth_version"] = request.user.session_version
        request.session["mfa_verified"] = True
        return Response({"user": user_payload(request.user), "recovery_codes": codes})


class MfaRecoveryRegenerateView(CsrfAPIView):
    @extend_schema(request=OtpInput, responses=schema.RecoveryResult)
    def post(self, request):
        values = OtpInput(data=request.data)
        values.is_valid(raise_exception=True)
        if not recent_login(request):
            return error("reauthentication_required", "Entre novamente para gerar códigos.", 403)
        if not limits_allow(request, "mfa", str(request.user.id)):
            return error("rate_limited", "Aguarde antes de tentar novamente.", 429)
        with transaction.atomic():
            device = TotpDevice.objects.select_for_update().filter(user=request.user, confirmed=True).first()
            if device is None or not verify_totp_locked(device, values.validated_data["otp"]):
                return error("invalid_otp", "Código de verificação inválido ou já utilizado.", 400)
            codes = issue_recovery_codes(request.user)
            audit(request, "auth.recovery_regenerated", request.user)
        return Response({"recovery_codes": codes})


class PlatformAdminPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and request.user.is_platform_admin and request.session.get("mfa_verified", False))


class PlatformUserInput(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    name = serializers.CharField(max_length=160)
    password = serializers.CharField(max_length=1024, write_only=True, trim_whitespace=False)
    is_platform_admin = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)


class PlatformUsersView(CsrfAPIView):
    permission_classes = [PlatformAdminPermission]

    @extend_schema(responses=schema.IdentityUser(many=True))
    def get(self, request):
        users = User.objects.order_by("email")
        if query := request.query_params.get("q", "").strip():
            users = users.filter(email__icontains=query)
        return Response([user_payload(user, include_memberships=False) for user in users[:200]])

    @extend_schema(request=PlatformUserInput, responses={201: schema.IdentityUser})
    def post(self, request):
        values = PlatformUserInput(data=request.data)
        values.is_valid(raise_exception=True)
        data = values.validated_data
        data["email"] = data["email"].lower()
        if User.objects.filter(email__iexact=data["email"]).exists():
            return error("email_exists", "Já existe uma conta com esse e-mail.", 409)
        candidate = User(email=data["email"], name=data["name"])
        try:
            validate_password(data["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        user = User.objects.create_user(**data)
        audit(request, "identity.user_created", user)
        return Response(user_payload(user, include_memberships=False), status=201)


class PlatformUserUpdateInput(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False)
    is_platform_admin = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class PlatformUserDetailView(CsrfAPIView):
    permission_classes = [PlatformAdminPermission]

    @extend_schema(request=PlatformUserUpdateInput, responses=schema.IdentityUser)
    def patch(self, request, user_id):
        values = PlatformUserUpdateInput(data=request.data)
        values.is_valid(raise_exception=True)
        data = values.validated_data
        if str(request.user.id) == str(user_id) and (data.get("is_active") is False or data.get("is_platform_admin") is False):
            return error("cannot_revoke_self", "Use outro administrador para remover seu acesso.", 409)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(id=user_id).first()
            if user is None:
                return error("not_found", "Usuário não encontrado.", 404)
            privilege_changed = any(key in data and data[key] != getattr(user, key) for key in ("is_active", "is_platform_admin"))
            for key, value in data.items():
                setattr(user, key, value)
            if privilege_changed:
                user.session_version += 1
            user.save()
            audit(request, "identity.user_updated", user, {"fields": sorted(data)})
        return Response(user_payload(user, include_memberships=False))


class RevokeSessionsView(CsrfAPIView):
    permission_classes = [PlatformAdminPermission]

    @extend_schema(request=schema.EmptyInput, responses={204: None})
    def post(self, request, user_id):
        if not User.objects.filter(id=user_id).update(session_version=F("session_version") + 1):
            return error("not_found", "Usuário não encontrado.", 404)
        audit(request, "identity.sessions_revoked", User.objects.get(id=user_id))
        return Response(status=204)
