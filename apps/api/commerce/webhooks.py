import stripe
from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from publishing.views import PublicView
from .models import WebhookReceipt
from .payments import process_event


class StripeWebhookView(PublicView):
    @extend_schema(exclude=True)
    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET or len(request.body) > 1024 * 1024:
            return Response(status=400)
        try:
            event = stripe.Webhook.construct_event(request.body, request.headers.get('Stripe-Signature', ''), settings.STRIPE_WEBHOOK_SECRET).to_dict()
        except (ValueError, stripe.SignatureVerificationError):
            return Response(status=400)
        if event.get('livemode'):
            return Response(status=400)
        with transaction.atomic():
            receipt, created = WebhookReceipt.objects.get_or_create(event_id=event['id'])
            if created:
                process_event(event)
        return Response({'received': True})
