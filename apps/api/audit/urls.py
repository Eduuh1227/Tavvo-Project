from django.urls import path

from .views import AuditListView

urlpatterns = [path("restaurants/<uuid:restaurant_id>/audit/", AuditListView.as_view(), name="audit-list")]
