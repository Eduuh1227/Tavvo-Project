from .models import AuditLog


def record(request, restaurant, action, resource, metadata=None):
    """Store deliberately selected metadata; never serialize incoming payloads."""
    return AuditLog.objects.create(
        restaurant=restaurant,
        actor_user=request.user if request.user.is_authenticated else None,
        action=action,
        resource_type=resource._meta.label_lower,
        resource_id=str(resource.pk),
        metadata=metadata or {},
        request_id=str(getattr(request, "request_id", ""))[:100],
    )
