"""
API URL configuration for the notifications app.

Mounted at /api/a/<team_slug>/notifications/.
"""

from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register(r"blasts", api.BlastViewSet, basename="blast")

urlpatterns = router.urls
