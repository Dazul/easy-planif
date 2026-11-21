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
from datetime import date

from django.test import TestCase

from hr.models import Employee

from .models import CustomUser


class UserEmployeeCreationViewTest(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="setup-admin",
            password="password",
            is_staff=True,
        )

    def test_staff_can_create_user_and_employee_together(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            "/users/",
            {
                "username": "new-employee",
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "Employee",
                "password1": "Strong-password-123",
                "password2": "Strong-password-123",
                "employee_number": "NEW001",
                "hourly_rate": "25.50",
                "hired_on": "2026-01-05",
                "left_on": "",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, "/users/")
        user = CustomUser.objects.get(username="new-employee")
        employee = Employee.objects.get(user=user)
        self.assertEqual(employee.employee_number, "NEW001")
        self.assertEqual(employee.hired_on, date(2026, 1, 5))

    def test_non_staff_cannot_create_user_and_employee(self):
        user = CustomUser.objects.create_user(
            username="regular-user",
            password="password",
        )
        self.client.force_login(user)

        response = self.client.post("/users/", {})

        self.assertEqual(response.status_code, 403)

    def test_duplicate_employee_number_returns_form_error(self):
        existing_user = CustomUser.objects.create_user(
            username="existing-user",
            password="test-password",
        )
        Employee.objects.create(
            user=existing_user,
            employee_number="DUP001",
            hourly_rate="25.50",
            hired_on=date(2026, 1, 5),
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            "/users/",
            {
                "username": "duplicate-employee",
                "email": "duplicate@example.com",
                "password1": "Strong-password-123",
                "password2": "Strong-password-123",
                "employee_number": "DUP001",
                "hourly_rate": "25.50",
                "hired_on": "2026-01-05",
                "left_on": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "An employee with this number already exists.",
            status_code=400,
        )
        self.assertFalse(
            CustomUser.objects.filter(username="duplicate-employee").exists()
        )

    def test_invalid_employee_dates_return_form_error(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            "/users/",
            {
                "username": "invalid-dates",
                "email": "invalid@example.com",
                "password1": "Strong-password-123",
                "password2": "Strong-password-123",
                "employee_number": "DATE001",
                "hourly_rate": "25.50",
                "hired_on": "2026-03-01",
                "left_on": "2026-02-01",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "The end date cannot be before the hire date.",
            status_code=400,
        )
        self.assertFalse(
            CustomUser.objects.filter(username="invalid-dates").exists()
        )
