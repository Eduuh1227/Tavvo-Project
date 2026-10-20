from rest_framework import serializers


class EmptyInput(serializers.Serializer):
    pass


class RestaurantSummary(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class MembershipSummary(serializers.Serializer):
    restaurant = RestaurantSummary()
    role = serializers.ChoiceField(choices=["manager", "staff"])


class IdentityUser(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField()
    is_platform_admin = serializers.BooleanField()
    is_active = serializers.BooleanField()
    mfa_enabled = serializers.BooleanField()
    memberships = MembershipSummary(many=True, required=False)


class MfaChallenge(serializers.Serializer):
    mfa_required = serializers.BooleanField()


class MfaSetupRequired(serializers.Serializer):
    mfa_enrollment_required = serializers.BooleanField()


class CsrfResult(serializers.Serializer):
    csrfToken = serializers.CharField()


class MessageResult(serializers.Serializer):
    message = serializers.CharField()


class MfaEnrollment(serializers.Serializer):
    secret = serializers.CharField()
    otpauth_url = serializers.CharField()


class RecoveryResult(serializers.Serializer):
    recovery_codes = serializers.ListField(child=serializers.CharField())


class MfaConfirmation(RecoveryResult):
    user = IdentityUser()
