"""
URL configuration for the events app.

All patterns are team-scoped and mounted at /a/<team_slug>/events/.
"""

from django.urls import path

from . import calendar_views, exports, slot_views, views

app_name = "events"

# Team-scoped URL patterns (tuple format provides the "events" namespace)
team_urlpatterns = (
    [
        # Event CRUD
        path("", views.event_list, name="event_list"),
        path("create/", views.event_create, name="event_create"),
        path("<int:pk>/", views.event_detail, name="event_detail"),
        path("<int:pk>/edit/", views.event_edit, name="event_edit"),
        path("<int:pk>/delete/", views.event_delete, name="event_delete"),
        # Calendar
        path("calendar/", calendar_views.event_calendar, name="event_calendar"),
        path("calendar/<int:year>/<int:month>/", calendar_views.event_calendar_month, name="event_calendar_month"),
        # Volunteer slots
        path("<int:event_pk>/slots/create/", slot_views.slot_create, name="slot_create"),
        path("<int:event_pk>/slots/<int:slot_pk>/edit/", slot_views.slot_edit, name="slot_edit"),
        path("<int:event_pk>/slots/<int:slot_pk>/delete/", slot_views.slot_delete, name="slot_delete"),
        # Signup / cancel
        path("<int:event_pk>/slots/<int:slot_pk>/signup/", slot_views.slot_signup, name="slot_signup"),
        path("<int:event_pk>/slots/<int:slot_pk>/cancel/", slot_views.slot_cancel_signup, name="slot_cancel_signup"),
        # Exports
        path("export/", exports.export_events_list, name="export_events"),
        path("<int:pk>/export-signups/", exports.export_event_signups, name="export_event_signups"),
    ],
    "events",
)
