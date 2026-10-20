from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("me/restaurants/", views.MyRestaurantsView.as_view(), name="my-restaurants"),
    path("auth/password-reset/request/", views.PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("auth/password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/mfa/enroll/", views.MfaEnrollView.as_view(), name="mfa-enroll"),
    path("auth/mfa/confirm/", views.MfaConfirmView.as_view(), name="mfa-confirm"),
    path("auth/mfa/recovery/regenerate/", views.MfaRecoveryRegenerateView.as_view(), name="mfa-recovery-regenerate"),
    path("platform/users/", views.PlatformUsersView.as_view(), name="platform-users"),
    path("platform/users/<uuid:user_id>/", views.PlatformUserDetailView.as_view(), name="platform-user-detail"),
    path("platform/users/<uuid:user_id>/revoke-sessions/", views.RevokeSessionsView.as_view(), name="revoke-sessions"),
]
