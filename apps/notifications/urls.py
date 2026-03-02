"""
URL configuration for the notifications app.

All patterns are team-scoped and mounted at /a/<team_slug>/notifications/.
"""

from django.urls import path

from . import exports, views

app_name = "notifications"

# Team-scoped URL patterns (tuple format provides the "notifications" namespace)
team_urlpatterns = (
    [
        path("", views.blast_list, name="blast_list"),
        path("compose/", views.blast_compose, name="blast_compose"),
        path("<int:pk>/", views.blast_detail, name="blast_detail"),
        path("<int:pk>/send/", views.blast_send, name="blast_send"),
        path("<int:pk>/export/", exports.export_blast_report, name="export_blast_report"),
        path("preferences/", views.contact_preferences, name="contact_preferences"),
    ],
    "notifications",
)
