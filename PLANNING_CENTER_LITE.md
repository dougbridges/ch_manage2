# Planning Center Lite - Implementation Plan

## Executive Summary

**Planning Center Lite** is a church event management SaaS for 100-500 member congregations,
built on top of the existing SaaS Pegasus / ch_manage2 Django infrastructure. It provides
event creation with volunteer slots, recurring volunteer rotations with reminders, and
SMS/email blasts — everything a mid-sized church needs to "keep Sunday from falling apart."

**Price point:** $19-79/month
**Target:** Mid-sized churches already paying for giving/streaming tools

---

## Existing Infrastructure Leveraged

The ch_manage2 codebase (SaaS Pegasus) already provides:

| Capability | Existing Implementation |
|---|---|
| Multi-tenancy | `Team` model + `BaseTeamModel` + `TeamScopedManager.for_team` |
| Roles/Permissions | `ROLE_ADMIN` / `ROLE_MEMBER` in `apps/teams/roles.py`, decorators in `apps/teams/decorators.py` |
| Auth & Invitations | django-allauth + `Invitation` model + email-based invitations |
| Email sending | `django.core.mail.send_mail` + HTML/text templates (see `apps/teams/invitations.py`) |
| Background jobs | Celery + Redis + django-celery-beat `DatabaseScheduler` |
| REST API | DRF + drf-spectacular + auto-generated OpenAPI client |
| Frontend stack | Tailwind 4 + DaisyUI 5 + Alpine.js 3 + HTMX 2 + Vite 7 |
| Base templates | `web/app/app_base.html` with sidebar nav, HTMX error handling |
| Test framework | `TestViewBase`, `TestLoginRequiredViewBase` test helpers |

---

## Architecture Decisions

Based on user choices and codebase analysis:

| Decision | Choice | Rationale |
|---|---|---|
| **Roles** | 3-tier: Admin, Coordinator, Member | Coordinators can manage volunteer slots/signups but can't delete events or send blasts |
| **SMS Provider** | Twilio | Industry standard, good Django support, abstract backend for future swap |
| **Calendar UI** | Server-rendered + HTMX | Consistent with project's HTMX-first approach; monthly grid rendered server-side |
| **Recurrence** | django-recurrence | Stores RRULE strings, generates occurrences; flexible and standards-based |

---

## New Django Apps

Three new Django apps, plus modifications to the existing `teams` app:

### 1. `apps.events` — Event Management & Volunteer Slots
### 2. `apps.notifications` — SMS/Email Blasts & Reminders
### 3. `apps.volunteers` — Volunteer Rotations & Scheduling

This separation follows single-responsibility: events own the calendar/CRUD, volunteers own
rotation logic, and notifications own all outbound messaging.

---

## Phase 1: Foundation — Roles & Event CRUD

**Goal:** Extend the role system, create the events app with basic CRUD, calendar view, and tests.

### 1A. Extend Role System

**File: `apps/teams/roles.py`**

```python
ROLE_ADMIN = "admin"
ROLE_COORDINATOR = "coordinator"  # NEW
ROLE_MEMBER = "member"

ROLE_CHOICES = (
    (ROLE_ADMIN, "Administrator"),
    (ROLE_COORDINATOR, "Coordinator"),  # NEW
    (ROLE_MEMBER, "Member"),
)

def is_coordinator(user, team) -> bool:
    """Check if user has coordinator role or higher on this team."""
    from .models import Membership
    return Membership.objects.filter(
        team=team, user=user, role__in=[ROLE_ADMIN, ROLE_COORDINATOR]
    ).exists()
```

**File: `apps/teams/decorators.py`** — Add `team_coordinator_required` decorator.

**Migration:** Add a data migration to handle existing memberships (no schema change needed
since `role` is already a CharField).

**Tests:**
- `test_coordinator_role` — Verify coordinator can access coordinator-gated views
- `test_coordinator_not_admin` — Verify coordinator cannot access admin-only views
- `test_member_not_coordinator` — Verify member cannot access coordinator views
- Update existing role tests to account for new role

### 1B. Events App — Models

**File: `apps/events/models.py`**

```
Event (extends BaseTeamModel)
├── title: CharField(max_length=200)
├── description: TextField(blank=True)
├── location: CharField(max_length=300, blank=True)
├── start_datetime: DateTimeField
├── end_datetime: DateTimeField
├── is_all_day: BooleanField(default=False)
├── recurrence: RecurrenceField(blank=True, null=True)  # django-recurrence
├── category: CharField (choices: worship, fellowship, outreach, youth, other)
├── created_by: FK → CustomUser
├── is_published: BooleanField(default=True)
└── Meta: ordering = ["start_datetime"]

VolunteerSlot (extends BaseTeamModel)
├── event: FK → Event (related_name="volunteer_slots")
├── role_name: CharField(max_length=100)  # e.g., "Nursery", "Ushers", "Food"
├── description: TextField(blank=True)
├── slots_needed: PositiveIntegerField(default=1)
└── Meta: ordering = ["role_name"]

VolunteerSignup (extends BaseTeamModel)
├── slot: FK → VolunteerSlot (related_name="signups")
├── volunteer: FK → CustomUser
├── note: TextField(blank=True)
├── status: CharField (choices: confirmed, tentative, cancelled)
└── Meta: unique_together = ["slot", "volunteer"]
```

**Managers:**
- All three models use `for_team = TeamScopedManager()` inherited from `BaseTeamModel`
- Custom manager on `Event` for date-range queries: `EventQuerySet` with
  `.upcoming()`, `.past()`, `.in_month(year, month)` methods

### 1C. Events App — Views & URLs

**URL structure** (team-scoped at `/a/<team_slug>/events/...`):

| URL Pattern | View | Access | Description |
|---|---|---|---|
| `events/` | `event_list` | Member+ | Calendar/list view of upcoming events |
| `events/calendar/` | `event_calendar` | Member+ | Monthly calendar grid (HTMX) |
| `events/calendar/<year>/<month>/` | `event_calendar_month` | Member+ | Specific month (HTMX partial) |
| `events/create/` | `event_create` | Coordinator+ | Create new event form |
| `events/<id>/` | `event_detail` | Member+ | Event detail with volunteer slots |
| `events/<id>/edit/` | `event_edit` | Coordinator+ | Edit event |
| `events/<id>/delete/` | `event_delete` | Admin only | Delete event |
| `events/<id>/slots/create/` | `slot_create` | Coordinator+ | Add volunteer slot to event |
| `events/<id>/slots/<slot_id>/edit/` | `slot_edit` | Coordinator+ | Edit slot |
| `events/<id>/slots/<slot_id>/delete/` | `slot_delete` | Coordinator+ | Delete slot |
| `events/<id>/slots/<slot_id>/signup/` | `slot_signup` | Member+ | Sign up for slot (HTMX) |
| `events/<id>/slots/<slot_id>/cancel/` | `slot_cancel_signup` | Member+ | Cancel own signup (HTMX) |

**View patterns:**
- Function-based views with `@login_and_team_required` or `@team_coordinator_required`
- All views accept `team_slug` as first URL parameter
- HTMX partials return fragments; full page requests return full templates
- Forms use Django ModelForm with team auto-set in `form.save(commit=False)`

### 1D. Events App — Templates

```
templates/events/
├── event_list.html              # Main events page with upcoming list + calendar link
├── event_detail.html            # Event detail with volunteer slots panel
├── event_form.html              # Create/edit event form
├── event_confirm_delete.html    # Delete confirmation
├── calendar.html                # Full calendar page
├── components/
│   ├── calendar_grid.html       # Monthly calendar grid (HTMX swappable)
│   ├── event_card.html          # Reusable event card for list views
│   ├── slot_list.html           # Volunteer slots for an event (HTMX swappable)
│   ├── slot_form.html           # Create/edit slot form (modal or inline)
│   ├── signup_button.html       # Sign up / cancel button (HTMX swappable)
│   └── event_category_badge.html # Category badge component
```

### 1E. Sidebar Navigation

**File: `templates/web/components/app_nav_menu_items.html`** — Add new section:

```html
<li class="menu-title">
  <span>{% translate "Church" %}</span>
</li>
<li>
  <a href="{% url 'events:event_list' team.slug %}">
    <i class="fa fa-calendar h-4 w-4"></i>
    {% translate "Events" %}
  </a>
</li>
<li>
  <a href="{% url 'events:event_calendar' team.slug %}">
    <i class="fa fa-calendar-days h-4 w-4"></i>
    {% translate "Calendar" %}
  </a>
</li>
```

(Volunteer and Notifications nav items added in later phases.)

### 1F. Phase 1 Tests

**File: `apps/events/tests/`**

```
apps/events/tests/
├── __init__.py
├── base.py                    # Test helpers: create_team, create_user, create_event, etc.
├── test_models.py             # Model creation, validation, querysets, managers
├── test_event_views.py        # CRUD views: permissions, form submission, HTMX responses
├── test_slot_views.py         # Volunteer slot CRUD + signup/cancel
├── test_calendar_views.py     # Calendar rendering, month navigation
├── test_forms.py              # Form validation, team auto-assignment
└── test_permissions.py        # Role-based access (admin, coordinator, member, anonymous)
```

**Test strategy:**
- Every view tested for: anonymous redirect, wrong-team 404, member access, coordinator access, admin access
- Model tests verify constraints (unique_together, required fields, cascading deletes)
- HTMX views tested with `HTTP_HX_REQUEST=True` header
- Factory functions in `base.py` for consistent test data creation
- Use `--keepdb` for faster test runs during development

**Estimated test count for Phase 1: ~60-80 tests**

### 1G. Phase 1 Dependencies

```
django-recurrence  # RRULE-based recurrence fields
```

Install via: `make uv add 'django-recurrence'`

---

## Phase 2: Notifications — Email & SMS Blasts

**Goal:** Build the notifications app with email and SMS sending, blast composition UI,
and delivery tracking.

### 2A. Notifications App — Models

**File: `apps/notifications/models.py`**

```
NotificationChannel (enum, not a model)
├── EMAIL = "email"
└── SMS = "sms"

MessageBlast (extends BaseTeamModel)
├── subject: CharField(max_length=200, blank=True)  # email subject; blank for SMS
├── body: TextField
├── channel: CharField(choices=NotificationChannel)
├── status: CharField (choices: draft, sending, sent, failed)
├── send_at: DateTimeField(null=True, blank=True)  # scheduled send; null = immediate
├── sent_at: DateTimeField(null=True, blank=True)
├── created_by: FK → CustomUser
├── recipient_filter: JSONField(default=dict)  # {"all": true} or {"event_id": 5} etc.
└── Meta: ordering = ["-created_at"]

MessageRecipient (extends BaseTeamModel)
├── blast: FK → MessageBlast (related_name="recipients")
├── user: FK → CustomUser
├── channel: CharField(choices=NotificationChannel)
├── status: CharField (choices: pending, sent, delivered, failed, bounced)
├── sent_at: DateTimeField(null=True)
├── external_id: CharField(blank=True)  # Twilio SID or email message-id
├── error_message: TextField(blank=True)
└── Meta: unique_together = ["blast", "user", "channel"]

ContactPreference (extends BaseTeamModel)
├── user: FK → CustomUser (related_name="contact_preferences")
├── phone_number: CharField(max_length=20, blank=True)  # E.164 format
├── receive_email: BooleanField(default=True)
├── receive_sms: BooleanField(default=False)
└── Meta: unique_together = ["team", "user"]
```

### 2B. Notification Backend Architecture

Abstract backend pattern for swappable providers:

**File: `apps/notifications/backends/base.py`**

```python
class NotificationBackend(ABC):
    """Abstract base class for notification delivery backends."""
    @abstractmethod
    def send_email(self, recipient, subject, body_html, body_text) -> str: ...
    @abstractmethod
    def send_sms(self, phone_number, body) -> str: ...
```

**File: `apps/notifications/backends/email_backend.py`** — Uses Django's `send_mail`
**File: `apps/notifications/backends/twilio_backend.py`** — Uses Twilio REST API
**File: `apps/notifications/backends/console_backend.py`** — Dev/test backend (logs to console)

**Settings:**
```python
# settings.py
NOTIFICATION_EMAIL_BACKEND = "apps.notifications.backends.email_backend.DjangoEmailBackend"
NOTIFICATION_SMS_BACKEND = "apps.notifications.backends.twilio_backend.TwilioBackend"
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", default="")
```

### 2C. Notifications App — Views & URLs

| URL Pattern | View | Access | Description |
|---|---|---|---|
| `notifications/` | `blast_list` | Coordinator+ | List of sent/scheduled blasts |
| `notifications/compose/` | `blast_compose` | Admin only | Compose new blast |
| `notifications/<id>/` | `blast_detail` | Coordinator+ | Delivery status/tracking |
| `notifications/<id>/send/` | `blast_send` | Admin only | Trigger send (POST) |
| `notifications/preferences/` | `contact_preferences` | Member+ | Own notification preferences |

### 2D. Celery Tasks

**File: `apps/notifications/tasks.py`**

```python
@shared_task
def send_blast(blast_id):
    """Process and send all recipients for a message blast."""

@shared_task
def send_single_notification(recipient_id):
    """Send a single notification to one recipient. Called per-recipient for retry isolation."""

@shared_task
def send_scheduled_blasts():
    """Periodic task: find blasts with send_at <= now and status=draft, trigger send."""
```

**Scheduled task** (added to `SCHEDULED_TASKS` in settings):
```python
"check-scheduled-blasts": {
    "task": "apps.notifications.tasks.send_scheduled_blasts",
    "schedule": schedules.crontab(minute="*/5"),  # every 5 minutes
},
```

### 2E. Phase 2 Templates

```
templates/notifications/
├── blast_list.html              # List of blasts with status badges
├── blast_compose.html           # Compose form with channel selector, recipient filter
├── blast_detail.html            # Delivery tracking with recipient statuses
├── contact_preferences.html     # User's own notification settings
├── components/
│   ├── blast_card.html          # Reusable blast summary card
│   ├── recipient_table.html     # Delivery status table (HTMX refreshable)
│   └── channel_selector.html    # Email/SMS toggle component
├── email/
│   ├── blast.html               # HTML email template for blasts
│   └── blast.txt                # Plain text email template
└── sms/
    └── blast.txt                # SMS body template
```

### 2F. Phase 2 Tests

```
apps/notifications/tests/
├── __init__.py
├── base.py                      # Helpers: create_blast, mock backends
├── test_models.py               # Model creation, status transitions, recipient filtering
├── test_views.py                # Compose, send, detail views + permissions
├── test_tasks.py                # Celery task tests (mock backends, verify delivery)
├── test_backends.py             # Backend unit tests (mock Twilio API, test email sending)
├── test_preferences.py          # Contact preference CRUD
└── test_scheduled_blasts.py     # Scheduled send logic
```

**Test strategy:**
- Mock Twilio API calls with `unittest.mock.patch`
- Mock Django email backend with `django.core.mail.outbox`
- Test Celery tasks synchronously with `CELERY_ALWAYS_EAGER=True`
- Test recipient filtering logic (all members, event attendees, etc.)
- Test status transitions (draft → sending → sent/failed)
- Test permission boundaries (only admins can compose/send blasts)

**Estimated test count for Phase 2: ~50-60 tests**

### 2G. Phase 2 Dependencies

```
twilio  # Twilio Python SDK for SMS
```

Install via: `make uv add 'twilio'`

---

## Phase 3: Volunteer Rotations & Scheduling

**Goal:** Build the volunteers app with auto-rotation scheduling, availability preferences,
and shift reminders.

### 3A. Volunteers App — Models

**File: `apps/volunteers/models.py`**

```
VolunteerProfile (extends BaseTeamModel)
├── user: FK → CustomUser
├── skills: JSONField(default=list)  # ["nursery", "ushers", "food", "music"]
├── max_services_per_month: PositiveIntegerField(default=4)
├── is_active: BooleanField(default=True)
├── notes: TextField(blank=True)
└── Meta: unique_together = ["team", "user"]

Availability (extends BaseTeamModel)
├── volunteer: FK → VolunteerProfile (related_name="availabilities")
├── date: DateField
├── is_available: BooleanField(default=False)  # blackout date when False
├── note: CharField(max_length=200, blank=True)
└── Meta: unique_together = ["volunteer", "date"]

RotationSchedule (extends BaseTeamModel)
├── name: CharField(max_length=200)  # e.g., "Sunday Morning Nursery Rotation"
├── event: FK → Event (null=True, blank=True)  # linked recurring event
├── slot_role_name: CharField(max_length=100)  # matches VolunteerSlot.role_name
├── rotation_strategy: CharField (choices: round_robin, weighted, manual)
├── volunteers: M2M → VolunteerProfile (through=RotationMembership)
├── is_active: BooleanField(default=True)
└── Meta: ordering = ["name"]

RotationMembership (extends BaseTeamModel)
├── schedule: FK → RotationSchedule
├── volunteer: FK → VolunteerProfile
├── order: PositiveIntegerField(default=0)  # for round-robin ordering
├── weight: PositiveIntegerField(default=1)  # for weighted scheduling
└── Meta: unique_together = ["schedule", "volunteer"], ordering = ["order"]

ScheduledShift (extends BaseTeamModel)
├── schedule: FK → RotationSchedule (related_name="shifts")
├── volunteer: FK → VolunteerProfile
├── event: FK → Event  # specific event occurrence
├── slot: FK → VolunteerSlot (null=True)
├── date: DateField
├── status: CharField (choices: scheduled, confirmed, declined, swapped)
├── reminder_sent: BooleanField(default=False)
└── Meta: unique_together = ["schedule", "volunteer", "date"]
```

### 3B. Rotation Algorithm

**File: `apps/volunteers/rotation.py`**

The rotation engine generates shifts for upcoming dates:

```python
def generate_rotation(schedule: RotationSchedule, start_date, end_date):
    """
    Generate ScheduledShift records for a rotation schedule.

    Algorithm (round_robin):
    1. Get ordered list of active volunteers in this rotation
    2. Get event occurrences in date range (from recurrence rule)
    3. Filter out dates where volunteer has blackout (Availability)
    4. Assign volunteers in order, skipping unavailable dates
    5. Track "last served" to maintain fairness
    6. Create ScheduledShift records (draft status)

    Algorithm (weighted):
    - Same as round_robin but frequency proportional to weight
    - Higher weight = more frequent scheduling
    """
```

### 3C. Volunteers App — Views & URLs

| URL Pattern | View | Access | Description |
|---|---|---|---|
| `volunteers/` | `volunteer_list` | Coordinator+ | List all volunteers and their profiles |
| `volunteers/profile/` | `my_volunteer_profile` | Member+ | Own volunteer profile/availability |
| `volunteers/profile/<id>/` | `volunteer_profile_detail` | Coordinator+ | View/edit a volunteer |
| `volunteers/availability/` | `my_availability` | Member+ | Set own blackout dates |
| `volunteers/rotations/` | `rotation_list` | Coordinator+ | List rotation schedules |
| `volunteers/rotations/create/` | `rotation_create` | Coordinator+ | Create rotation schedule |
| `volunteers/rotations/<id>/` | `rotation_detail` | Coordinator+ | View schedule + upcoming shifts |
| `volunteers/rotations/<id>/edit/` | `rotation_edit` | Coordinator+ | Edit rotation |
| `volunteers/rotations/<id>/generate/` | `rotation_generate` | Coordinator+ | Generate shifts (POST) |
| `volunteers/rotations/<id>/shifts/` | `rotation_shifts` | Coordinator+ | View/manage shifts |
| `volunteers/shifts/my/` | `my_shifts` | Member+ | Own upcoming shifts |
| `volunteers/shifts/<id>/confirm/` | `shift_confirm` | Member+ | Confirm shift (HTMX) |
| `volunteers/shifts/<id>/decline/` | `shift_decline` | Member+ | Decline shift (HTMX) |

### 3D. Celery Tasks for Reminders

**File: `apps/volunteers/tasks.py`**

```python
@shared_task
def send_shift_reminders():
    """
    Periodic task: Find shifts in the next N days that haven't had reminders sent.
    Send email/SMS reminders based on volunteer's contact preferences.
    """

@shared_task
def auto_generate_rotations():
    """
    Periodic task: For active rotation schedules, auto-generate shifts
    for the next 4 weeks if they don't already exist.
    """
```

**Scheduled tasks:**
```python
"send-shift-reminders": {
    "task": "apps.volunteers.tasks.send_shift_reminders",
    "schedule": schedules.crontab(minute=0, hour=8),  # daily at 8 AM
},
"auto-generate-rotations": {
    "task": "apps.volunteers.tasks.auto_generate_rotations",
    "schedule": schedules.crontab(minute=0, hour=2, day_of_week=1),  # Monday 2 AM
},
```

### 3E. Phase 3 Templates

```
templates/volunteers/
├── volunteer_list.html           # Grid/table of volunteers with skills badges
├── volunteer_profile.html        # Volunteer profile form (own or coordinator view)
├── availability.html             # Calendar-style availability picker
├── rotation_list.html            # List of rotation schedules
├── rotation_form.html            # Create/edit rotation
├── rotation_detail.html          # Schedule detail with shift calendar
├── my_shifts.html                # Member's upcoming shifts dashboard
├── components/
│   ├── volunteer_card.html       # Volunteer summary card
│   ├── availability_calendar.html # Alpine.js interactive calendar
│   ├── shift_card.html           # Shift card with confirm/decline buttons
│   ├── rotation_members.html     # Drag-to-reorder member list (Alpine.js)
│   └── shift_status_badge.html   # Status badge component
```

### 3F. Phase 3 Tests

```
apps/volunteers/tests/
├── __init__.py
├── base.py                       # Helpers: create_volunteer_profile, etc.
├── test_models.py                # Model creation, constraints, managers
├── test_views.py                 # All volunteer views + permissions
├── test_rotation.py              # Rotation algorithm: round_robin, weighted, availability
├── test_availability.py          # Blackout date logic, calendar rendering
├── test_tasks.py                 # Celery tasks: reminders, auto-generate
├── test_shift_management.py      # Confirm, decline, swap workflows
└── test_my_shifts.py             # Member's shift dashboard
```

**Test strategy:**
- Rotation algorithm tested extensively with edge cases:
  - All volunteers unavailable on a date
  - Single volunteer in rotation
  - Uneven weights
  - Blackout dates overlapping
- Celery tasks tested with mocked notification backends
- Shift status transitions tested (scheduled → confirmed/declined)
- Availability calendar HTMX interactions tested

**Estimated test count for Phase 3: ~70-80 tests**

---

## Phase 4: Event Reminders & Notification Integration

**Goal:** Wire events and volunteers together with the notification system for automated
reminders and event announcements.

### 4A. Event Notification Triggers

**File: `apps/events/signals.py`** (used sparingly, well-documented)

```python
# Signal: When a new event is published, optionally notify all team members
# Signal: When an event is updated (time/location change), notify signed-up volunteers
```

**File: `apps/events/notifications.py`** — High-level notification helpers:

```python
def notify_event_created(event):
    """Send announcement to all team members about a new event."""

def notify_event_updated(event, changes):
    """Notify signed-up volunteers about event changes."""

def notify_signup_confirmation(signup):
    """Send confirmation to volunteer who just signed up."""
```

### 4B. Reminder Celery Tasks

**File: `apps/events/tasks.py`**

```python
@shared_task
def send_event_reminders():
    """
    Periodic task: Send reminders for events happening in the next 24-48 hours.
    Uses contact preferences to determine email vs SMS.
    """

@shared_task
def send_volunteer_shift_reminders():
    """
    Periodic task: Remind volunteers of their upcoming shifts (2 days before).
    """
```

**Scheduled tasks:**
```python
"send-event-reminders": {
    "task": "apps.events.tasks.send_event_reminders",
    "schedule": schedules.crontab(minute=0, hour=9),  # daily 9 AM
},
```

### 4C. Phase 4 Tests

```
apps/events/tests/test_notifications.py    # Event notification triggers
apps/events/tests/test_reminder_tasks.py   # Reminder Celery tasks
apps/notifications/tests/test_integration.py # End-to-end notification flow
```

**Estimated test count for Phase 4: ~30-40 tests**

---

## Phase 5: API Layer

**Goal:** Expose REST API endpoints for potential mobile app or third-party integrations.

### 5A. API Endpoints

**File: `apps/events/api.py`** — DRF ViewSets

| Endpoint | Methods | Access |
|---|---|---|
| `/api/events/` | GET, POST | Member+ (GET), Coordinator+ (POST) |
| `/api/events/<id>/` | GET, PUT, DELETE | Member+ (GET), Coordinator+ (PUT), Admin (DELETE) |
| `/api/events/<id>/slots/` | GET, POST | Member+ (GET), Coordinator+ (POST) |
| `/api/events/<id>/slots/<id>/signup/` | POST, DELETE | Member+ |
| `/api/volunteers/profile/` | GET, PUT | Member+ (own), Coordinator+ (others) |
| `/api/volunteers/shifts/` | GET | Member+ (own) |
| `/api/volunteers/shifts/<id>/confirm/` | POST | Member+ (own) |
| `/api/notifications/blasts/` | GET, POST | Admin only |

### 5B. Serializers

**Files:** `apps/events/serializers.py`, `apps/volunteers/serializers.py`, `apps/notifications/serializers.py`

- Use `TeamModelSerializer` base (if exists) or standard DRF serializers with team auto-set
- Nested serializers for Event → VolunteerSlots → Signups
- Read-only serializers for list views, write serializers for create/update

### 5C. API Tests

```
apps/events/tests/test_api.py
apps/volunteers/tests/test_api.py
apps/notifications/tests/test_api.py
```

**Estimated test count for Phase 5: ~40-50 tests**

---

## Phase 6: Polish & Production Readiness

### 6A. Dashboard Enhancements

Replace the default `app_home.html` with a church dashboard showing:
- Upcoming events (next 7 days)
- My upcoming volunteer shifts
- Recent blasts sent
- Quick actions (create event, compose blast)

### 6B. Search & Filtering

- Event list filtering by category, date range
- Volunteer search by name, skill
- Blast filtering by status, channel

### 6C. Data Export

- Export volunteer roster as CSV
- Export event attendee/signup lists as CSV
- Export blast delivery reports

### 6D. Admin Site Registration

Register all new models in Django admin for superuser access:
- `apps/events/admin.py`
- `apps/notifications/admin.py`
- `apps/volunteers/admin.py`

### 6E. Translation Markup Audit

Verify all user-facing strings use `gettext_lazy` / `translate` / `blocktranslate trimmed`.

### 6F. Performance Optimization

- Add database indexes on frequently queried fields (event dates, shift dates)
- Add `select_related` / `prefetch_related` on all list views
- Add pagination to all list views (events, volunteers, blasts)

---

## File Organization Summary

```
apps/
├── events/
│   ├── __init__.py
│   ├── admin.py                 # Django admin registration
│   ├── apps.py                  # AppConfig
│   ├── forms.py                 # EventForm, VolunteerSlotForm
│   ├── models.py                # Event, VolunteerSlot, VolunteerSignup
│   ├── managers.py              # EventQuerySet with .upcoming(), .in_month()
│   ├── urls.py                  # urlpatterns + team_urlpatterns
│   ├── views.py                 # Event CRUD views (split if >250 lines)
│   ├── slot_views.py            # Slot + signup views
│   ├── calendar_views.py        # Calendar rendering views
│   ├── api.py                   # DRF viewsets
│   ├── serializers.py           # DRF serializers
│   ├── notifications.py         # Event notification helpers
│   ├── signals.py               # Post-save signals (if needed)
│   ├── tasks.py                 # Celery tasks (reminders)
│   ├── migrations/
│   └── tests/
│       ├── __init__.py
│       ├── base.py
│       ├── test_models.py
│       ├── test_event_views.py
│       ├── test_slot_views.py
│       ├── test_calendar_views.py
│       ├── test_forms.py
│       ├── test_permissions.py
│       ├── test_api.py
│       ├── test_notifications.py
│       └── test_reminder_tasks.py
├── notifications/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py                 # BlastComposeForm, ContactPreferenceForm
│   ├── models.py                # MessageBlast, MessageRecipient, ContactPreference
│   ├── urls.py
│   ├── views.py                 # Blast CRUD + preferences
│   ├── api.py
│   ├── serializers.py
│   ├── tasks.py                 # send_blast, send_scheduled_blasts
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract NotificationBackend
│   │   ├── email_backend.py     # Django email backend
│   │   ├── twilio_backend.py    # Twilio SMS backend
│   │   └── console_backend.py   # Dev/test console backend
│   ├── migrations/
│   └── tests/
│       ├── __init__.py
│       ├── base.py
│       ├── test_models.py
│       ├── test_views.py
│       ├── test_tasks.py
│       ├── test_backends.py
│       ├── test_preferences.py
│       ├── test_scheduled_blasts.py
│       └── test_integration.py
├── volunteers/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py                 # VolunteerProfileForm, RotationForm, AvailabilityForm
│   ├── models.py                # VolunteerProfile, Availability, RotationSchedule, etc.
│   ├── urls.py
│   ├── views.py                 # Volunteer views (split if needed)
│   ├── rotation_views.py        # Rotation schedule views
│   ├── shift_views.py           # Shift management views
│   ├── api.py
│   ├── serializers.py
│   ├── rotation.py              # Rotation algorithm engine
│   ├── tasks.py                 # Celery tasks (reminders, auto-generate)
│   ├── migrations/
│   └── tests/
│       ├── __init__.py
│       ├── base.py
│       ├── test_models.py
│       ├── test_views.py
│       ├── test_rotation.py
│       ├── test_availability.py
│       ├── test_tasks.py
│       ├── test_shift_management.py
│       ├── test_my_shifts.py
│       └── test_api.py
└── teams/
    └── (existing, modified)
        ├── roles.py             # Add ROLE_COORDINATOR
        └── decorators.py        # Add team_coordinator_required

templates/
├── events/                      # (see Phase 1 template tree)
├── notifications/               # (see Phase 2 template tree)
└── volunteers/                  # (see Phase 3 template tree)
```

---

## Settings Changes Summary

```python
# settings.py additions

# In INSTALLED_APPS / PROJECT_APPS:
"apps.events.apps.EventsConfig",
"apps.notifications.apps.NotificationsConfig",
"apps.volunteers.apps.VolunteersConfig",
"recurrence",  # django-recurrence (in THIRD_PARTY_APPS)

# Notification settings:
NOTIFICATION_EMAIL_BACKEND = env(
    "NOTIFICATION_EMAIL_BACKEND",
    default="apps.notifications.backends.email_backend.DjangoEmailBackend"
)
NOTIFICATION_SMS_BACKEND = env(
    "NOTIFICATION_SMS_BACKEND",
    default="apps.notifications.backends.console_backend.ConsoleBackend"
)
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", default="")

# Reminder settings:
EVENT_REMINDER_HOURS_BEFORE = 24
SHIFT_REMINDER_DAYS_BEFORE = 2

# Scheduled tasks (add to SCHEDULED_TASKS dict):
"check-scheduled-blasts": {...}
"send-event-reminders": {...}
"send-shift-reminders": {...}
"auto-generate-rotations": {...}
```

---

## URL Registration in Main urls.py

**File: `ch_manage2/urls.py`**

```python
# Add to team_urlpatterns:
from apps.events.urls import team_urlpatterns as event_team_urls
from apps.notifications.urls import team_urlpatterns as notification_team_urls
from apps.volunteers.urls import team_urlpatterns as volunteer_team_urls

team_urlpatterns = [
    path("", include(web_team_urls)),
    path("team/", include(single_team_urls)),
    path("events/", include(event_team_urls)),          # NEW
    path("notifications/", include(notification_team_urls)),  # NEW
    path("volunteers/", include(volunteer_team_urls)),   # NEW
]
```

---

## Implementation Order & Dependencies

```
Phase 1: Foundation (Roles + Event CRUD + Calendar)
   └── No external dependencies beyond django-recurrence
   └── ~2-3 weeks of development
   └── Deliverable: Working event calendar with volunteer sign-ups

Phase 2: Notifications (Email + SMS Blasts)
   └── Depends on Phase 1 (events exist for event-based blasts)
   └── ~2 weeks of development
   └── Deliverable: Admin can compose and send email/SMS blasts

Phase 3: Volunteer Rotations
   └── Depends on Phase 1 (events + volunteer slots)
   └── Can overlap with Phase 2
   └── ~2-3 weeks of development
   └── Deliverable: Automated volunteer rotation scheduling

Phase 4: Integration & Reminders
   └── Depends on Phase 2 + Phase 3
   └── ~1 week of development
   └── Deliverable: Automated reminders for events and shifts

Phase 5: API Layer
   └── Depends on all above phases (models exist)
   └── ~1 week of development
   └── Deliverable: REST API for mobile/third-party access

Phase 6: Polish & Production
   └── Depends on all above
   └── ~1 week of development
   └── Deliverable: Production-ready with admin, exports, performance
```

---

## Total Estimated Test Coverage

| Phase | Estimated Tests |
|---|---|
| Phase 1: Events & Calendar | 60-80 |
| Phase 2: Notifications | 50-60 |
| Phase 3: Volunteers | 70-80 |
| Phase 4: Integration | 30-40 |
| Phase 5: API | 40-50 |
| Phase 6: Polish | 10-20 |
| **Total** | **260-330 tests** |

---

## Code Comment Standards

Per the user's request for extensive comments, all new code will follow these standards:

1. **Module-level docstrings** — Every `.py` file starts with a docstring explaining its purpose
2. **Class docstrings** — Every model, form, serializer, and view class has a docstring
3. **Method docstrings** — All public methods have docstrings explaining purpose, args, and return values
4. **Inline comments** — Complex logic blocks have inline comments explaining the "why"
5. **Template comments** — Django template comments (`{# ... #}`) for non-obvious template logic
6. **TODO markers** — `# TODO:` for known future improvements
7. **Type hints** — All new function signatures include type hints

Example:
```python
# apps/events/models.py
"""
Event models for Planning Center Lite.

This module defines the core event management models: Event (the main calendar entry),
VolunteerSlot (positions that need filling), and VolunteerSignup (who signed up for what).
All models extend BaseTeamModel for automatic team scoping.
"""

class Event(BaseTeamModel):
    """
    A church event (service, potluck, VBS, youth trip, etc.).

    Events can be one-time or recurring (via django-recurrence RRULE field).
    Each event can have multiple VolunteerSlots attached to it.

    Access control:
    - All team members can view published events
    - Coordinators and admins can create/edit events
    - Only admins can delete events
    """
```

---

## Migration Strategy

1. Create each app with `make uv run 'pegasus startapp <app_name>'` where appropriate, or manually
2. Create models incrementally — start with `Event`, then `VolunteerSlot`, then `VolunteerSignup`
3. Run `make migrations` after each model addition
4. Run `make migrate` to apply
5. Verify with `make test` after each migration

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Recurrence complexity | Use well-tested `django-recurrence`; extensive tests for edge cases |
| SMS costs | Start with console backend in dev; rate-limit sends; admin-only blast access |
| Notification delivery | Per-recipient task isolation; retry logic; delivery status tracking |
| Rotation fairness | Comprehensive algorithm tests; manual override capability |
| Performance at scale | Queryset optimization; pagination; database indexes; Celery for heavy work |
