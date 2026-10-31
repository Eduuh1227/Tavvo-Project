from django.urls import path
from . import views
from .webhooks import StripeWebhookView

urlpatterns = [
    path('public/restaurants/<slug:slug>/ordering/', views.PublicOrderSettingsView.as_view()),
    path('public/restaurants/<slug:slug>/orders/', views.PublicOrderCreateView.as_view()),
    path('public/restaurants/<slug:slug>/orders/<uuid:order_id>/', views.PublicOrderDetailView.as_view()),
    path('public/restaurants/<slug:slug>/orders/<uuid:order_id>/checkout/', views.PublicCheckoutView.as_view()),
    path('restaurants/<uuid:restaurant_id>/ordering/', views.OrderSettingsView.as_view()),
    path('restaurants/<uuid:restaurant_id>/orders/', views.OrderViewSet.as_view({'get': 'list'})),
    path('restaurants/<uuid:restaurant_id>/orders/<uuid:pk>/', views.OrderViewSet.as_view({'get': 'retrieve'})),
    path('restaurants/<uuid:restaurant_id>/orders/<uuid:pk>/transition/', views.OrderViewSet.as_view({'post': 'change_status'})),
    path('restaurants/<uuid:restaurant_id>/orders/<uuid:pk>/received-payment/', views.OrderViewSet.as_view({'post': 'received_payment'})),
    path('restaurants/<uuid:restaurant_id>/orders/<uuid:pk>/refund/', views.OrderViewSet.as_view({'post': 'refund'})),
    path('restaurants/<uuid:restaurant_id>/billing/', views.BillingView.as_view()),
    path('restaurants/<uuid:restaurant_id>/billing/checkout/', views.BillingCheckoutView.as_view()),
    path('restaurants/<uuid:restaurant_id>/billing/portal/', views.BillingPortalView.as_view()),
    path('payments/stripe/webhook/', StripeWebhookView.as_view()),
]
