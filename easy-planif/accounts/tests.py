from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


class CustomUserStrTest(TestCase):
    def test_str_returns_username(self):
        user = CustomUser.objects.create_user(username="alice")
        self.assertEqual(str(user), "alice")


class UsersViewTest(TestCase):
    def setUp(self):
        CustomUser.objects.create_user(username="plain", password="secret")
        self.staff = CustomUser.objects.create_user(
            username="staff", password="secret", is_staff=True
        )

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("users"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_non_staff_forbidden(self):
        plain = CustomUser.objects.get(username="plain")
        self.client.force_login(plain)
        response = self.client.get(reverse("users"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_list_users(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("users"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "plain")
        self.assertContains(response, "staff")
