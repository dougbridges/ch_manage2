from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class PendingMigrationsTests(TestCase):
    # This tests that there are no pending database migrations that haven't been added.
    # for more on the approach and motivation, see https://adamj.eu/tech/2024/06/23/django-test-pending-migrations/
    # Project app labels to check (excludes third-party packages like django-recurrence
    # whose pending migrations live inside site-packages and are not under our control).
    PROJECT_APP_LABELS = [
        "users",
        "dashboard",
        "api",
        "web",
        "teams",
        "chat",
        "events",
        "notifications",
        "volunteers",
    ]

    def test_no_pending_migrations(self):
        out = StringIO()
        try:
            call_command(
                "makemigrations",
                *self.PROJECT_APP_LABELS,
                check_changes=True,
                stdout=out,
                stderr=StringIO(),
            )
        except SystemExit:  # pragma: no cover
            raise AssertionError("Pending migrations:\n" + out.getvalue()) from None
