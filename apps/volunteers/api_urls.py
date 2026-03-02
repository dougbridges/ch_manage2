"""
API URL configuration for the volunteers app.

Mounted at /api/a/<team_slug>/volunteers/.
"""

from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register(r"profiles", api.VolunteerProfileViewSet, basename="volunteer-profile")
router.register(r"shifts", api.ShiftViewSet, basename="shift")

urlpatterns = router.urls
