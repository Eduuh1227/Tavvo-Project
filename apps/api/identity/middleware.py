from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import timezone


class SessionPolicyMiddleware:
    """Enforce revocation, idle expiry and absolute expiry before API permissions."""
    limited_paths = {
        "/v1/auth/csrf", "/v1/auth/logout", "/v1/auth/mfa/enroll", "/v1/auth/mfa/confirm",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = int(timezone.now().timestamp())
            session = request.session
            started = session.get("auth_started_at", 0)
            seen = session.get("auth_seen_at", 0)
            version = session.get("auth_version")
            absolute = getattr(settings, "TAVVO_SESSION_ABSOLUTE_SECONDS", 43200)
            idle = getattr(settings, "TAVVO_SESSION_IDLE_SECONDS", 1800)
            if version != request.user.session_version or now - started >= absolute or now - seen >= idle:
                logout(request)
            else:
                session["auth_seen_at"] = now
                if request.user.is_platform_admin and not session.get("mfa_verified", False):
                    if request.path.rstrip("/") not in self.limited_paths:
                        return JsonResponse({"code": "mfa_required", "message": "Configure e confirme o segundo fator."}, status=403)
        return self.get_response(request)
