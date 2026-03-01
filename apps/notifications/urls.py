"""
URL configuration for the notifications app.

All patterns are team-scoped and mounted at /a/<team_slug>/notifications/.
"""

from django.urls import path

from . import views

app_name = "notifications"

team_urlpatterns = [
    path("", views.blast_list, name="blast_list"),
    path("compose/", views.blast_compose, name="blast_compose"),
    path("<int:pk>/", views.blast_detail, name="blast_detail"),
    path("<int:pk>/send/", views.blast_send, name="blast_send"),
    path("preferences/", views.contact_preferences, name="contact_preferences"),
]
