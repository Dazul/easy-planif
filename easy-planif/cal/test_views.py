from datetime import datetime, timezone

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from tasks.models import Tasks, Authorizations

from .models import Event


class ToggleReplacementTest(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="owner", password="secret"
        )
        self.other = CustomUser.objects.create_user(
            username="other", password="secret"
        )
        self.task = Tasks.objects.create(task_name="T1")
        Authorizations.objects.create(user=self.owner, task=self.task)
        self.event = Event.objects.create(
            user=self.owner,
            tasks=self.task,
            date=datetime(2019, 10, 5, tzinfo=timezone.utc),
            is_available=False,
        )

    def url(self, event):
        return f"{reverse('cal:toggle_replacement')}?event_id={event.id}"

    def test_owner_can_toggle_replacement_on(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url(self.event))
        self.assertRedirects(response, "/calendar", fetch_redirect_response=False)
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_replaceable)

    def test_owner_can_toggle_replacement_off(self):
        self.event.is_replaceable = True
        self.event.save()
        self.client.force_login(self.owner)
        self.client.get(self.url(self.event))
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_replaceable)

    def test_other_user_cannot_toggle(self):
        self.client.force_login(self.other)
        response = self.client.get(self.url(self.event))
        self.assertEqual(response.status_code, 403)
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_replaceable)

    def test_owner_cannot_toggle_availability_event(self):
        available = Event.objects.create(
            user=self.owner,
            date=datetime(2019, 10, 6, tzinfo=timezone.utc),
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.url(available))
        self.assertEqual(response.status_code, 403)
        available.refresh_from_db()
        self.assertFalse(available.is_replaceable)


class UpdateEventTest(TestCase):
    def setUp(self):
        self.planner = CustomUser.objects.create_user(
            username="planner", password="secret"
        )
        # Grant the planner the assign_task permission
        assign_task = Permission.objects.get(codename="assign_task")
        self.planner.user_permissions.add(assign_task)

        self.worker = CustomUser.objects.create_user(
            username="worker", password="secret"
        )
        self.task = Tasks.objects.create(task_name="T1")
        Authorizations.objects.create(user=self.worker, task=self.task)

        self.available_event = Event.objects.create(
            user=self.worker,
            date=datetime(2019, 10, 5, tzinfo=timezone.utc),
        )

    def post_update(self, week_date="None", task="None"):
        return self.client.post(
            reverse("cal:planning_event_update"),
            {
                "event_id": self.available_event.id,
                "task_id": self.task.id,
                "week_date": week_date,
                "task": task,
            },
        )

    def test_assign_task_to_available_event(self):
        self.client.force_login(self.planner)
        # Event starts as a standard availability
        self.available_event.is_if_needed = True
        self.available_event.save()
        response = self.post_update()
        self.assertRedirects(response, "/planning", fetch_redirect_response=False)
        self.available_event.refresh_from_db()
        self.assertFalse(self.available_event.is_available)
        self.assertFalse(self.available_event.is_if_needed)
        self.assertEqual(self.available_event.tasks, self.task)

    def test_missing_permission_is_forbidden(self):
        self.client.force_login(self.worker)
        response = self.post_update()
        self.assertEqual(response.status_code, 403)
        self.available_event.refresh_from_db()
        self.assertTrue(self.available_event.is_available)

    def test_post_params_preserved_in_redirect(self):
        self.client.force_login(self.planner)
        response = self.post_update(
            week_date="2019-10-07", task=str(self.task.id)
        )
        self.assertRedirects(
            response,
            "/planning?week_date=2019-10-07&task=" + str(self.task.id),
            fetch_redirect_response=False,
        )


class PlanningViewAccessTest(TestCase):
    def setUp(self):
        Tasks.objects.create(task_name="T1")

    def test_anonymous_forbidden(self):
        # raise_exception=True rejects anonymous users with 403 too
        response = self.client.get(reverse("cal:planning"))
        self.assertEqual(response.status_code, 403)

    def test_without_permission_forbidden(self):
        user = CustomUser.objects.create_user(username="plain", password="secret")
        self.client.force_login(user)
        response = self.client.get(reverse("cal:planning"))
        self.assertEqual(response.status_code, 403)

    def test_with_assign_task_permission_allowed(self):
        planner = CustomUser.objects.create_user(
            username="planner", password="secret"
        )
        assign_task = Permission.objects.get(codename="assign_task")
        planner.user_permissions.add(assign_task)
        self.client.force_login(planner)
        response = self.client.get(reverse("cal:planning"))
        self.assertEqual(response.status_code, 200)


class PlanningRenderingTest(TestCase):
    def setUp(self):
        self.planner = CustomUser.objects.create_user(
            username="planner", password="secret"
        )
        assign_task = Permission.objects.get(codename="assign_task")
        self.planner.user_permissions.add(assign_task)

        self.worker = CustomUser.objects.create_user(
            username="worker", password="secret"
        )
        self.t1 = Tasks.objects.create(task_name="T1")
        self.t2 = Tasks.objects.create(task_name="T2")
        Authorizations.objects.create(user=self.worker, task=self.t1)
        Authorizations.objects.create(user=self.worker, task=self.t2)
        # availability on Monday of the displayed week
        self.available = Event.objects.create(
            user=self.worker,
            date=datetime(2019, 10, 7, tzinfo=timezone.utc),
        )
        self.client.force_login(self.planner)

    def planning_url(self, **params):
        return reverse("cal:planning") + "?" + "&".join(
            f"{k}={v}" for k, v in params.items()
        )

    def test_no_header_task_shows_dropdown(self):
        response = self.client.get(
            reverse("cal:planning"), {"week_date": "2019-10-07"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<select")
        self.assertContains(response, '<option value="1">T1</option>')
        self.assertContains(response, '<option value="2">T2</option>')
        self.assertNotContains(response, "quick-assign")

    def test_header_task_shows_quick_assign_box(self):
        response = self.client.get(
            self.planning_url(week_date="2019-10-07", task=self.t1.id)
        )
        self.assertEqual(response.status_code, 200)
        # dropdown replaced by a one-click quick-assign box
        self.assertNotContains(response, "<select")
        self.assertContains(response, "quick-assign")
        # submits the selected task directly
        self.assertContains(response, f'name="task_id" value="{self.t1.id}"')
        self.assertContains(response, ">T1</button>")

    def test_header_task_unauthorized_user_renders_dashes(self):
        # 'other' holds no authorization for T1: their cell shows dashes
        # instead of the quick-assign box
        other = CustomUser.objects.create_user(username="other", password="secret")
        Event.objects.create(
            user=other,
            date=datetime(2019, 10, 7, tzinfo=timezone.utc),
        )
        response = self.client.get(
            self.planning_url(week_date="2019-10-07", task=self.t1.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "---")
        # 'other' row must not contain a submit box
        self.assertNotContains(response, 'name="event_id" value="2"')


class CalendarViewTest(TestCase):
    """Note: CalendarView is currently NOT login-protected."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="u1", password="secret"
        )

    def test_anonymous_access_allowed(self):
        # Document current behavior: no @login_required on CalendarView
        response = self.client.get(reverse("cal:calendar"))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_shows_calendar(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cal:calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "calendar")

    def test_own_event_rendered_as_available(self):
        d = datetime(2019, 10, 5, tzinfo=timezone.utc)
        Event.objects.create(user=self.user, date=d)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("cal:calendar"), {"month": "2019-10"}
        )
        self.assertContains(response, "Available")

    def test_own_event_rendered_as_if_needed(self):
        d = datetime(2019, 10, 5, tzinfo=timezone.utc)
        Event.objects.create(user=self.user, date=d, is_if_needed=True)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("cal:calendar"), {"month": "2019-10"}
        )
        self.assertContains(response, "Available (if needed)")

    def test_empty_day_cell_is_clickable(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("cal:calendar"), {"month": "2019-10"}
        )
        # free days expose the whole cell as a click target
        self.assertContains(response, "free-day")


class ToggleIfNeededTest(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="owner", password="secret"
        )
        self.other = CustomUser.objects.create_user(
            username="other", password="secret"
        )
        self.event = Event.objects.create(
            user=self.owner,
            date=datetime(2019, 10, 5, tzinfo=timezone.utc),
        )

    def url(self, event):
        return f"{reverse('cal:toggle_if_needed')}?event_id={event.id}"

    def test_owner_can_toggle_to_if_needed(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url(self.event))
        self.assertRedirects(response, "/calendar", fetch_redirect_response=False)
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_if_needed)

    def test_owner_can_cycle_back_to_removed(self):
        self.event.is_if_needed = True
        self.event.save()
        self.client.force_login(self.owner)
        self.client.get(self.url(self.event))
        # cycling from "if needed" removes the availability entirely
        with self.assertRaises(Event.DoesNotExist):
            Event.objects.get(pk=self.event.pk)

    def test_other_user_cannot_toggle(self):
        self.client.force_login(self.other)
        response = self.client.get(self.url(self.event))
        self.assertEqual(response.status_code, 403)
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_if_needed)

    def test_cannot_toggle_assigned_event(self):
        task = Tasks.objects.create(task_name="T1")
        Authorizations.objects.create(user=self.owner, task=task)
        assigned = Event.objects.create(
            user=self.owner,
            tasks=task,
            date=datetime(2019, 10, 6, tzinfo=timezone.utc),
            is_available=False,
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.url(assigned))
        self.assertEqual(response.status_code, 403)
        assigned.refresh_from_db()
        self.assertFalse(assigned.is_if_needed)


class CreateEventTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="u1", password="secret"
        )

    def valid_payload(self, day="05", if_needed="false"):
        # EventForm uses %d-%m-%Y input format (day-month-year)
        return {
            "is_available": "True",
            "is_if_needed": if_needed,
            "date": f"{day}-10-2019",
        }

    def test_create_available_event(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("cal:event_new"), self.valid_payload()
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get(user=self.user)
        self.assertTrue(event.is_available)
        self.assertFalse(event.is_if_needed)
        self.assertEqual(event.date, datetime(2019, 10, 5, tzinfo=timezone.utc))

    def test_create_if_needed_event(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("cal:event_new"), self.valid_payload(if_needed="true")
        )
        self.assertEqual(response.status_code, 201)
        event = Event.objects.get(user=self.user)
        self.assertTrue(event.is_available)
        self.assertTrue(event.is_if_needed)

    def test_duplicate_date_rejected(self):
        # UniqueConstraint (user, date) is checked in Model.clean(),
        # not in the form (user is not a form field), so saving a
        # duplicate raises before the view returns cleanly.
        self.client.force_login(self.user)
        self.client.post(reverse("cal:event_new"), self.valid_payload())
        with self.assertRaises(Exception):
            self.client.post(reverse("cal:event_new"), self.valid_payload())
        self.assertEqual(Event.objects.count(), 1)

    def test_iso_date_also_accepted(self):
        # DateField falls back to ISO YYYY-MM-DD even with custom
        # input_formats
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("cal:event_new"),
            {"is_available": "True", "date": "2019-10-05"},
        )
        self.assertEqual(response.status_code, 201)
        event = Event.objects.get(user=self.user)
        self.assertEqual(event.date, datetime(2019, 10, 5, tzinfo=timezone.utc))

    def test_garbage_date_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("cal:event_new"),
            {"is_available": "True", "date": "not-a-date"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)

    def test_missing_fields_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("cal:event_new"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)
