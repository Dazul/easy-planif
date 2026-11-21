from datetime import date, datetime, time, timezone

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from tasks.models import Tasks, Authorizations

from .models import Event, Booking, BookingType, ReplacementRequest


from .models import Event, Booking, BookingType, ReplacementRequest


class ReplaceRequestTest(TestCase):
    """Clicking a replaceable event now creates a pending
    ReplacementRequest instead of taking the event directly."""

    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="owner", password="secret"
        )
        self.replacer = CustomUser.objects.create_user(
            username="replacer", password="secret"
        )
        self.unauthorized = CustomUser.objects.create_user(
            username="unauthorized", password="secret"
        )
        self.task = Tasks.objects.create(task_name="T1")
        Authorizations.objects.create(user=self.owner, task=self.task)
        Authorizations.objects.create(user=self.replacer, task=self.task)
        self.event = Event.objects.create(
            user=self.owner,
            tasks=self.task,
            date=datetime(2019, 10, 5, tzinfo=timezone.utc),
            is_available=False,
            is_replaceable=True,
        )

    def url(self, event):
        return f"{reverse('cal:replace')}?event_id={event.id}"

    def test_authorized_user_creates_pending_request(self):
        self.client.force_login(self.replacer)
        response = self.client.get(self.url(self.event))
        self.assertRedirects(
            response, reverse("cal:replacements"), fetch_redirect_response=False
        )
        request = ReplacementRequest.objects.get(event=self.event)
        self.assertEqual(request.replacement_user, self.replacer)
        self.assertEqual(request.status, ReplacementRequest.Status.PENDING)
        # event unchanged until validated
        self.event.refresh_from_db()
        self.assertEqual(self.event.user, self.owner)
        self.assertTrue(self.event.is_replaceable)

    def test_unauthorized_user_cannot_request(self):
        self.client.force_login(self.unauthorized)
        response = self.client.get(self.url(self.event))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ReplacementRequest.objects.count(), 0)

    def test_second_requester_gets_forbidden(self):
        extra = CustomUser.objects.create_user(
            username="extra", password="secret"
        )
        Authorizations.objects.create(user=extra, task=self.task)
        self.client.force_login(self.replacer)
        self.client.get(self.url(self.event))
        self.client.force_login(extra)
        response = self.client.get(self.url(self.event))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ReplacementRequest.objects.count(), 1)

    def test_repeat_request_by_same_user_is_noop(self):
        self.client.force_login(self.replacer)
        self.client.get(self.url(self.event))
        response = self.client.get(self.url(self.event))
        self.assertRedirects(
            response, reverse("cal:replacements"), fetch_redirect_response=False
        )
        self.assertEqual(ReplacementRequest.objects.count(), 1)

    def test_owner_cannot_replace_self(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url(self.event))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ReplacementRequest.objects.count(), 0)

    def test_non_replaceable_event_cannot_be_requested(self):
        self.event.is_replaceable = False
        self.event.save()
        self.client.force_login(self.replacer)
        response = self.client.get(self.url(self.event))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ReplacementRequest.objects.count(), 0)

    def test_replacements_calendar_marks_pending_slot(self):
        ReplacementRequest.objects.create(
            event=self.event, replacement_user=self.replacer
        )
        self.client.force_login(self.replacer)
        response = self.client.get(
            reverse("cal:replacements"),
            {"week_date": "2019-09-30"},
        )
        self.assertContains(response, "requested by replacer")
        # the pending slot is not takeable anymore
        self.assertNotContains(response, "replacements/replace?event_id=")


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

    def test_if_needed_shows_info_and_assignment_form(self):
        self.available.is_if_needed = True
        self.available.save()
        # no header task: dropdown plus the if-needed marker
        response = self.client.get(
            self.planning_url(week_date="2019-10-07")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If needed")
        self.assertContains(response, "<select")

    def test_if_needed_shows_quick_assign_with_info(self):
        self.available.is_if_needed = True
        self.available.save()
        # header task selected: quick-assign button plus marker
        response = self.client.get(
            self.planning_url(week_date="2019-10-07", task=self.t1.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If needed")
        self.assertContains(response, "quick-assign")

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


class PlanningUserStatsTest(TestCase):
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
        Authorizations.objects.create(user=self.worker, task=self.t1)

        # October 2019: the displayed week Oct 7-13 lies fully inside it
        # Mon Oct 7: assigned task
        Event.objects.create(
            user=self.worker,
            tasks=self.t1,
            date=datetime(2019, 10, 7, tzinfo=timezone.utc),
            is_available=False,
        )
        # Tue Oct 8: standard availability
        Event.objects.create(
            user=self.worker,
            date=datetime(2019, 10, 8, tzinfo=timezone.utc),
        )
        # Wed Oct 9: if-needed availability (counts as bookable)
        Event.objects.create(
            user=self.worker,
            date=datetime(2019, 10, 9, tzinfo=timezone.utc),
            is_if_needed=True,
        )
        # Later in the same month but outside the displayed week:
        # Thu Oct 24 assigned, Fri Oct 25 available -> included in stats
        Event.objects.create(
            user=self.worker,
            tasks=self.t1,
            date=datetime(2019, 10, 24, tzinfo=timezone.utc),
            is_available=False,
        )
        Event.objects.create(
            user=self.worker,
            date=datetime(2019, 10, 25, tzinfo=timezone.utc),
        )
        self.client.force_login(self.planner)

    def test_stats_shown_next_to_username(self):
        # 2 assigned of 5 bookable October days
        response = self.client.get(
            reverse("cal:planning"), {"week_date": "2019-10-09"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "(2/5)")

    def test_stats_use_month_of_week_monday(self):
        # Week straddling Sep/Oct: Monday Sep 30 belongs to September,
        # so stats must count September events only.
        Event.objects.create(
            user=self.worker,
            date=datetime(2019, 9, 30, tzinfo=timezone.utc),
        )
        response = self.client.get(
            reverse("cal:planning"), {"week_date": "2019-10-03"}
        )
        self.assertEqual(response.status_code, 200)
        # September: 0 assigned of 1 bookable
        self.assertContains(response, "(0/1)")
        self.assertNotContains(response, "(2/5)")

    def test_no_bookable_days_hides_stats(self):
        # A user with events only in another month never appears in the
        # October week, so no stats are rendered for them.
        idle = CustomUser.objects.create_user(username="idle", password="secret")
        Event.objects.create(
            user=idle,
            date=datetime(2019, 11, 4, tzinfo=timezone.utc),
        )
        response = self.client.get(
            reverse("cal:planning"), {"week_date": "2019-10-09"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "idle")

    def test_zero_ratio_still_rendered(self):
        # A user whose month events are all availabilities shows (0/n)
        rested = CustomUser.objects.create_user(username="rested", password="secret")
        Event.objects.create(
            user=rested,
            date=datetime(2019, 10, 7, tzinfo=timezone.utc),
        )
        Event.objects.create(
            user=rested,
            date=datetime(2019, 10, 8, tzinfo=timezone.utc),
            is_if_needed=True,
        )
        response = self.client.get(
            reverse("cal:planning"), {"week_date": "2019-10-09"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "(0/2)")


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

class BookingsViewTest(TestCase):
    def setUp(self):
        self.viewer = CustomUser.objects.create_user(username="viewer", password="secret")
        view_perm = Permission.objects.get(codename="bookings_view")
        self.viewer.user_permissions.add(view_perm)

        self.bt = BookingType.objects.create(booking_type="School", color="#ff0000")
        self.booking = Booking.objects.create(
            booking_name="Class of 2019",
            booking_type=self.bt,
            date=date(2019, 10, 5),
            hour_start=time(10, 0),
            hour_end=time(20, 0),
            group_leader_name="Boby",
            group_leader_address="home",
            group_leader_email="boby@home.com",
            nbr_adult=10,
            nbr_child=10,
            nbr_wheelchair=0,
            price_adult=10,
            price_child=10,
            price_total=100,
        )

    def url(self, **params):
        base = reverse("cal:bookings")
        if params:
            base += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        return base

    def test_requires_bookings_view_permission(self):
        plain = CustomUser.objects.create_user(username="plain", password="secret")
        self.client.force_login(plain)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)

    def test_anonymous_forbidden(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)

    def test_booking_rendered_with_type_color(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url(month="2019-10"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Class of 2019")
        # color code from the booking type as the entry background
        self.assertContains(response, 'background-color: #ff0000;')

    def test_booking_without_type_rendered_neutral(self):
        Booking.objects.create(
            booking_name="No type party",
            date=date(2019, 10, 6),
            hour_start=time(10, 0),
            hour_end=time(20, 0),
            group_leader_name="Ann",
            group_leader_address="home",
            group_leader_email="ann@home.com",
            nbr_adult=5,
            nbr_child=0,
            price_adult=10,
            price_child=10,
            price_total=50,
        )
        self.client.force_login(self.viewer)
        response = self.client.get(self.url(month="2019-10"))
        self.assertContains(response, "No type party")
        # untyped bookings get a neutral grey background
        self.assertContains(response, "background-color: #eeeeee;")

class BookingDetailEditTest(TestCase):
    def setUp(self):
        self.manager = CustomUser.objects.create_user(
            username="manager", password="secret"
        )
        manage_perm = Permission.objects.get(codename="bookings_manager")
        self.manager.user_permissions.add(manage_perm)
        self.viewer = CustomUser.objects.create_user(
            username="viewer", password="secret"
        )
        view_perm = Permission.objects.get(codename="bookings_view")
        self.viewer.user_permissions.add(view_perm)

        self.bt = BookingType.objects.create(booking_type="School", color="#ff0000")
        self.booking = Booking.objects.create(
            booking_name="Class of 2019",
            booking_type=self.bt,
            date=date(2019, 10, 5),
            hour_start=time(10, 0),
            hour_end=time(20, 0),
            group_leader_name="Boby",
            group_leader_address="home",
            group_leader_email="boby@home.com",
            nbr_adult=10,
            nbr_child=10,
            nbr_wheelchair=0,
            price_adult=10,
            price_child=10,
            price_total=200,  # 10x10 + 10x10, meal not included
        )

    def test_calendar_entry_links_to_detail(self):
        self.client.force_login(self.viewer)
        response = self.client.get(
            reverse("cal:bookings"), {"month": "2019-10"}
        )
        self.assertContains(response, f'href="bookings/{self.booking.id}"')

    def test_detail_view_shows_fields(self):
        self.client.force_login(self.viewer)
        response = self.client.get(
            reverse("cal:booking_detail", args=[self.booking.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Class of 2019")
        self.assertContains(response, "Boby")

    def test_detail_requires_view_permission(self):
        plain = CustomUser.objects.create_user(username="plain", password="secret")
        self.client.force_login(plain)
        response = self.client.get(
            reverse("cal:booking_detail", args=[self.booking.id])
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_can_edit_booking(self):
        self.client.force_login(self.manager)
        # GET the edit form first to ensure it renders
        get_response = self.client.get(
            reverse("cal:booking_edit", args=[self.booking.id])
        )
        self.assertEqual(get_response.status_code, 200)
        response = self.client.post(
            reverse("cal:booking_edit", args=[self.booking.id]),
            {
                "booking_name": "Renamed group",
                "booking_type": self.bt.id,
                "date": "2019-10-05",
                "come_all_weather": "False",
                "hour_start": "10:00",
                "hour_end": "20:00",
                "group_leader_name": "Boby",
                "group_leader_address": "home",
                "group_leader_email": "boby@home.com",
                "nbr_adult": "10",
                "nbr_child": "10",
                "nbr_wheelchair": "0",
                "price_adult": "10",
                "price_child": "10",
                "meal_included": "False",
                "meal_price_adult": "12",
                "meal_price_child": "6",
                "price_total": "200",  # 10x10 + 10x10, meal not included
            },
        )
        self.assertRedirects(
            response,
            reverse("cal:booking_detail", args=[self.booking.id]),
            fetch_redirect_response=False,
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_name, "Renamed group")
        self.assertEqual(self.booking.last_author, self.manager)

    def test_viewer_cannot_edit_booking(self):
        self.client.force_login(self.viewer)
        response = self.client.get(
            reverse("cal:booking_edit", args=[self.booking.id])
        )
        self.assertEqual(response.status_code, 403)

class BookingDayViewTest(TestCase):
    def setUp(self):
        self.viewer = CustomUser.objects.create_user(username="viewer", password="secret")
        view_perm = Permission.objects.get(codename="bookings_view")
        self.viewer.user_permissions.add(view_perm)
        self.bt = BookingType.objects.create(booking_type="School", color="#ff0000")
        # two bookings on the same day, one on another day
        self.morning = Booking.objects.create(
            booking_name="Morning group",
            booking_type=self.bt,
            date=date(2019, 10, 5),
            hour_start=time(9, 0),
            hour_end=time(12, 0),
            group_leader_name="Boby",
            group_leader_address="home",
            group_leader_email="boby@home.com",
            nbr_adult=10, nbr_child=0, price_adult=10, price_child=0,
            price_total=100,
        )
        self.afternoon = Booking.objects.create(
            booking_name="Afternoon group",
            date=date(2019, 10, 5),
            hour_start=time(14, 0),
            hour_end=time(18, 0),
            group_leader_name="Ann",
            group_leader_address="home",
            group_leader_email="ann@home.com",
            nbr_adult=5, nbr_child=2, price_adult=10, price_child=10,
            price_total=70,
        )
        Booking.objects.create(
            booking_name="Other day group",
            date=date(2019, 10, 6),
            hour_start=time(9, 0),
            hour_end=time(12, 0),
            group_leader_name="Max",
            group_leader_address="home",
            group_leader_email="max@home.com",
            nbr_adult=1, nbr_child=0, price_adult=10, price_child=0,
            price_total=10,
        )
        self.client.force_login(self.viewer)

    def test_month_view_links_day_to_day_view(self):
        response = self.client.get(
            reverse("cal:bookings"), {"month": "2019-10"}
        )
        self.assertContains(response, "bookings/day/2019-10-05")

    def test_day_view_lists_only_that_day_sorted_by_hour(self):
        response = self.client.get(
            reverse("cal:booking_day", args=["2019-10-05"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Morning group")
        self.assertContains(response, "Afternoon group")
        self.assertNotContains(response, "Other day group")
        # sorted by start hour: morning before afternoon
        self.assertLess(
            response.content.decode().index("Morning group"),
            response.content.decode().index("Afternoon group"),
        )

    def test_day_view_links_to_details(self):
        response = self.client.get(
            reverse("cal:booking_day", args=["2019-10-05"])
        )
        self.assertContains(
            response,
            reverse("cal:booking_detail", args=[self.morning.id]),
        )
        self.assertContains(
            response,
            reverse("cal:booking_detail", args=[self.afternoon.id]),
        )

    def test_day_view_requires_permission(self):
        plain = CustomUser.objects.create_user(username="plain", password="secret")
        self.client.force_login(plain)
        response = self.client.get(
            reverse("cal:booking_day", args=["2019-10-05"])
        )
        self.assertEqual(response.status_code, 403)

class BookingPriceAutocomputeTest(TestCase):
    def setUp(self):
        self.manager = CustomUser.objects.create_user(
            username="manager", password="secret"
        )
        manage_perm = Permission.objects.get(codename="bookings_manager")
        self.manager.user_permissions.add(manage_perm)
        self.client.force_login(self.manager)

    def valid_payload(self, **overrides):
        payload = dict(
            booking_name="G1",
            date="2019-10-05",
            come_all_weather="False",
            hour_start="10:00",
            hour_end="20:00",
            group_leader_name="Boby",
            group_leader_address="home",
            group_leader_email="boby@home.com",
            nbr_adult="10",
            nbr_child="5",
            nbr_wheelchair="0",
            price_adult="20",
            price_child="10",
            meal_included="True",
            meal_price_adult="12",
            meal_price_child="6",
            price_total="400",  # 10*20 + 5*10 + 10*12 + 5*6
        )
        payload.update(overrides)
        return payload

    def test_correct_total_accepted(self):
        response = self.client.post(
            reverse("cal:add_booking"), self.valid_payload()
        )
        self.assertRedirects(
            response, "/bookings", fetch_redirect_response=False
        )
        self.assertEqual(Booking.objects.count(), 1)

    def test_tampered_total_rejected(self):
        response = self.client.post(
            reverse("cal:add_booking"),
            self.valid_payload(price_total="999"),
        )
        self.assertEqual(response.status_code, 200)  # form re-rendered
        self.assertEqual(Booking.objects.count(), 0)
        self.assertContains(response, "must be 400")

    def test_meal_excluded_from_total(self):
        # meal_included False: meal prices must not count
        response = self.client.post(
            reverse("cal:add_booking"),
            self.valid_payload(meal_included="False", price_total="250"),
        )
        self.assertRedirects(
            response, "/bookings", fetch_redirect_response=False
        )
        self.assertEqual(Booking.objects.count(), 1)

    def test_edit_form_rejects_wrong_total_too(self):
        booking = Booking.objects.create(
            booking_name="G1",
            date=date(2019, 10, 5),
            hour_start=time(10, 0),
            hour_end=time(20, 0),
            group_leader_name="Boby",
            group_leader_address="home",
            group_leader_email="boby@home.com",
            nbr_adult=10,
            nbr_child=5,
            price_adult=20,
            price_child=10,
            meal_included=True,
            meal_price_adult=12,
            meal_price_child=6,
            price_total=400,
            last_author=self.manager,
        )
        response = self.client.post(
            reverse("cal:booking_edit", args=[booking.id]),
            self.valid_payload(price_total="1"),
        )
        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.price_total, 400)

    def test_js_hooks_present_on_form(self):
        response = self.client.get(reverse("cal:add_booking"))
        self.assertContains(response, "data-price-total")
        self.assertContains(response, "data-price-part")
