"""
URL configuration for the volunteers app.

All patterns are team-scoped and mounted at /a/<team_slug>/volunteers/.
"""

from django.urls import path

from . import views

app_name = "volunteers"

team_urlpatterns = [
    # Volunteer list & profiles
    path("", views.volunteer_list, name="volunteer_list"),
    path("profile/", views.my_volunteer_profile, name="my_volunteer_profile"),
    path("profile/<int:pk>/", views.volunteer_profile_detail, name="volunteer_profile_detail"),
    # Availability
    path("availability/", views.my_availability, name="my_availability"),
    # Rotation schedules
    path("rotations/", views.rotation_list, name="rotation_list"),
    path("rotations/create/", views.rotation_create, name="rotation_create"),
    path("rotations/<int:pk>/", views.rotation_detail, name="rotation_detail"),
    path("rotations/<int:pk>/edit/", views.rotation_edit, name="rotation_edit"),
    path("rotations/<int:pk>/generate/", views.rotation_generate, name="rotation_generate"),
    path("rotations/<int:pk>/shifts/", views.rotation_shifts, name="rotation_shifts"),
    # My shifts
    path("shifts/my/", views.my_shifts, name="my_shifts"),
    path("shifts/<int:pk>/confirm/", views.shift_confirm, name="shift_confirm"),
    path("shifts/<int:pk>/decline/", views.shift_decline, name="shift_decline"),
]
