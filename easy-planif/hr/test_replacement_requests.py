from datetime import datetime, timezone

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from cal.models import Event, ReplacementRequest
from tasks.models import Authorizations, Tasks


class ReplacementRequestHRTest(TestCase):
    """HR staff validate or refuse pending replacement requests."""

    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="staff", password="secret", is_staff=True
        )
        self.owner = CustomUser.objects.create_user(
            username="owner", password="secret"
        )
        self.replacer = CustomUser.objects.create_user(
            username="replacer", password="secret"
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
        self.request = ReplacementRequest.objects.create(
            event=self.event, replacement_user=self.replacer
        )

    def post(self, action, user=None):
        self.client.force_login(user or self.staff)
        return self.client.post(
            reverse("hr:replacement_requests"),
            {"request_id": self.request.pk, "action": action},
        )

    def test_page_requires_staff(self):
        plain = CustomUser.objects.create_user(username="plain", password="secret")
        self.client.force_login(plain)
        response = self.client.get(reverse("hr:replacement_requests"))
        self.assertEqual(response.status_code, 403)

    def test_pending_requests_listed(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("hr:replacement_requests"))
        self.assertContains(response, "replacer")
        self.assertContains(response, "owner")
        self.assertContains(response, "Validate")

    def test_validate_applies_replacement(self):
        response = self.post("validate")
        self.assertRedirects(
            response, reverse("hr:replacement_requests"),
            fetch_redirect_response=False,
        )
        self.request.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(self.request.status, ReplacementRequest.Status.VALIDATED)
        self.assertEqual(self.request.reviewed_by, self.staff)
        self.assertEqual(self.event.user, self.replacer)
        self.assertFalse(self.event.is_replaceable)

    def test_refuse_frees_slot_and_keeps_record(self):
        response = self.post("refuse")
        self.assertRedirects(
            response, reverse("hr:replacement_requests"),
            fetch_redirect_response=False,
        )
        self.request.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(self.request.status, ReplacementRequest.Status.REFUSED)
        self.assertEqual(self.request.reviewed_by, self.staff)
        # event untouched: still owned by the original user
        self.assertEqual(self.event.user, self.owner)
        self.assertTrue(self.event.is_replaceable)

    def test_decided_request_cannot_be_decided_again(self):
        self.post("validate")
        response = self.post("refuse")
        self.assertEqual(response.status_code, 404)  # no longer pending
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, ReplacementRequest.Status.VALIDATED)

    def test_validate_without_authorization_gracefully_fails(self):
        # authorization revoked between request and review
        Authorizations.objects.filter(
            user=self.replacer, task=self.task
        ).delete()
        response = self.post("validate")
        self.assertRedirects(
            response, reverse("hr:replacement_requests"),
            fetch_redirect_response=False,
        )
        self.request.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(self.request.status, ReplacementRequest.Status.PENDING)
        self.assertEqual(self.event.user, self.owner)

    def test_history_filter_shows_all_requests(self):
        self.post("refuse")
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("hr:replacement_requests"), {"status": "all"}
        )
        self.assertContains(response, "Refused")
