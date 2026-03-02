"""
API URL configuration for the events app.

Mounted at /api/a/<team_slug>/events/.
"""

from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register(r"", api.EventViewSet, basename="event")

urlpatterns = router.urls

# Nested slot URLs need manual registration
from django.urls import include, path

slot_router = DefaultRouter()
slot_router.register(r"", api.SlotViewSet, basename="slot")

urlpatterns += [
    path("<int:event_pk>/slots/", include(slot_router.urls)),
]
