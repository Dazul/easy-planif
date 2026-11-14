from datetime import date, time

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.test import TestCase
from django.contrib import admin

from accounts.models import CustomUser

from .admin import EmployeeAdmin, PayrollPaymentAdmin, WorkEntryAdmin
from .models import Employee, PayrollPayment, WorkEntry


class EmployeeModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            username="e1", email="", password=""
        )

    def create_employee(self, **overrides):
        defaults = {
            "user": self.user,
            "employee_number": "EMP001",
            "hourly_rate": "25.50",
            "hired_on": date(2026, 1, 5),
        }
        defaults.update(overrides)
        return Employee(**defaults)

    def test_employee_creation(self):
        employee = self.create_employee()
        employee.save()
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(employee.employee_number, "EMP001")
        self.assertEqual(employee.hourly_rate, 25.50)
        self.assertTrue(employee.is_active)
        self.assertIsNone(employee.left_on)

    def test_employee_str(self):
        employee = self.create_employee()
        employee.save()
        self.assertIn("EMP001", str(employee))
        self.assertIn("e1", str(employee))

    def test_unique_employee_number(self):
        self.create_employee().save()
        other_user = CustomUser.objects.create_superuser(
            username="e2", email="", password=""
        )
        duplicate = self.create_employee(user=other_user)
        with self.assertRaises(ValidationError):
            duplicate.save()

    def test_duplicate_user_rejected(self):
        """Only one Employee profile per user (OneToOneField)."""
        self.create_employee().save()
        other = self.create_employee(employee_number="EMP002")
        with self.assertRaises(ValidationError):
            other.save()

    def test_left_on_before_hired_on_invalid(self):
        employee = self.create_employee(left_on=date(2025, 12, 31))
        with self.assertRaises(ValidationError):
            employee.save()

    def test_left_on_equal_hired_on_is_valid(self):
        employee = self.create_employee(left_on=date(2026, 1, 5))
        employee.save()
        self.assertEqual(employee.left_on, date(2026, 1, 5))

    def test_left_on_after_hired_on_is_valid(self):
        employee = self.create_employee(left_on=date(2026, 3, 1))
        employee.save()
        self.assertEqual(Employee.objects.count(), 1)


class EmployeeListViewTest(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="manager",
            password="password",
            is_staff=True,
        )
        self.employee_user = CustomUser.objects.create_user(
            username="employee",
            password="password",
        )
        Employee.objects.create(
            user=self.employee_user,
            employee_number="EMP001",
            hourly_rate="25.50",
            hired_on=date(2026, 1, 5),
            left_on=date(2026, 3, 1),
            is_active=False,
        )

    def test_staff_can_view_employees(self):
        self.client.force_login(self.staff)

        response = self.client.get("/hr/employees/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EMP001")
        self.assertContains(response, "25.50")
        self.assertContains(response, "Inactive")

    def test_non_staff_cannot_view_employees(self):
        self.client.force_login(self.employee_user)

        response = self.client.get("/hr/employees/")

        self.assertEqual(response.status_code, 403)


class HRAdminRegistrationTest(TestCase):
    def test_hr_models_are_registered_with_expected_admin_classes(self):
        self.assertIsInstance(admin.site._registry[Employee], EmployeeAdmin)
        self.assertIsInstance(admin.site._registry[WorkEntry], WorkEntryAdmin)
        self.assertIsInstance(
            admin.site._registry[PayrollPayment],
            PayrollPaymentAdmin,
        )


class WorkCalendarViewTest(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="calendar-manager",
            password="password",
            is_staff=True,
        )
        self.employee_user = CustomUser.objects.create_user(
            username="calendar-employee",
            password="password",
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            employee_number="CAL001",
            hourly_rate="25.50",
            hired_on=date(2026, 1, 5),
        )

    def test_staff_can_view_work_calendar(self):
        WorkEntry.objects.create(
            employee=self.employee,
            work_date=date(2026, 10, 8),
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_minutes=30,
        )
        self.client.force_login(self.staff)

        response = self.client.get("/hr/time-entries/?year=2026&month=10")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "October 2026")
        self.assertContains(response, "calendar-employee")
        self.assertContains(response, "08:00")
        self.assertContains(response, "17:00")
        self.assertContains(response, "calendar-day-past")

    def test_non_staff_cannot_view_work_calendar(self):
        self.client.force_login(self.employee_user)

        response = self.client.get("/hr/time-entries/")

        self.assertEqual(response.status_code, 403)

    def test_calendar_marks_future_days(self):
        self.client.force_login(self.staff)

        response = self.client.get("/hr/time-entries/?year=2099&month=10")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "calendar-day-future")


class WorkDayViewTest(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="day-manager",
            password="password",
            is_staff=True,
        )
        employee_user = CustomUser.objects.create_user(
            username="day-employee",
            password="password",
        )
        employee = Employee.objects.create(
            user=employee_user,
            employee_number="DAY001",
            hourly_rate="25.50",
            hired_on=date(2026, 1, 5),
        )
        self.entry = WorkEntry.objects.create(
            employee=employee,
            work_date=date(2026, 10, 8),
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_minutes=30,
            notes="Client project",
        )

    def test_staff_can_view_day_details(self):
        self.client.force_login(self.staff)

        response = self.client.get("/hr/time-entries/2026-10-08/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Client project")
        self.assertContains(response, "8.50")

    def test_staff_can_approve_entry(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            "/hr/time-entries/2026-10-08/",
            {"entry_id": self.entry.pk},
        )

        self.assertRedirects(response, "/hr/time-entries/2026-10-08/")
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, WorkEntry.Status.APPROVED)
        self.assertEqual(self.entry.approved_by, self.staff)

    def test_staff_can_edit_and_save_entry(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            "/hr/time-entries/2026-10-08/",
            {
                "entry_id": self.entry.pk,
                "start_time": "09:00",
                "end_time": "18:00",
                "break_minutes": "45",
                "notes": "Updated project",
                "action": "save",
            },
        )

        self.assertRedirects(response, "/hr/time-entries/2026-10-08/")
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.start_time, time(9, 0))
        self.assertEqual(self.entry.break_minutes, 45)
        self.assertEqual(self.entry.notes, "Updated project")

    def test_staff_can_add_entry_to_day(self):
        self.client.force_login(self.staff)
        employee = self.entry.employee

        response = self.client.post(
            "/hr/time-entries/2026-10-08/",
            {
                "employee": employee.pk,
                "start_time": "18:00",
                "end_time": "20:00",
                "notes": "Evening shift",
            },
        )

        self.assertRedirects(response, "/hr/time-entries/2026-10-08/")
        entry = WorkEntry.objects.get(
            employee=employee,
            start_time=time(18, 0),
        )
        self.assertEqual(entry.break_minutes, 30)
        self.assertEqual(entry.work_date, date(2026, 10, 8))


class EmployeeWorkCalendarViewTest(TestCase):
    def setUp(self):
        self.employee_user = CustomUser.objects.create_user(
            username="self-calendar",
            password="password",
        )
        self.other_user = CustomUser.objects.create_user(
            username="other-calendar",
            password="password",
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            employee_number="SELF001",
            hourly_rate="25.50",
            hired_on=date(2026, 1, 5),
        )
        other_employee = Employee.objects.create(
            user=self.other_user,
            employee_number="OTHER001",
            hourly_rate="30.00",
            hired_on=date(2026, 1, 5),
        )
        WorkEntry.objects.create(
            employee=self.employee,
            work_date=date(2026, 10, 8),
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_minutes=30,
        )
        WorkEntry.objects.create(
            employee=other_employee,
            work_date=date(2026, 10, 8),
            start_time=time(9, 0),
            end_time=time(18, 0),
        )

    def test_employee_only_sees_own_entries(self):
        self.client.force_login(self.employee_user)

        response = self.client.get(
            "/hr/my-time-entries/?year=2026&month=10"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "self-calendar")
        self.assertNotContains(response, "other-calendar")

    def test_employee_day_view_is_read_only(self):
        self.client.force_login(self.employee_user)

        response = self.client.get("/hr/my-time-entries/2026-10-08/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "08:00")
        self.assertNotContains(response, "Approve")


class PayrollPaymentModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="payroll-employee",
            password="password",
        )
        self.employee = Employee.objects.create(
            user=self.user,
            employee_number="PAY001",
            hourly_rate="25.50",
            hired_on=date(2026, 1, 5),
        )
        self.admin = CustomUser.objects.create_user(
            username="payroll-admin",
            password="password",
            is_staff=True,
        )

    def test_payment_is_pending_until_approved(self):
        payment = PayrollPayment.objects.create(
            employee=self.employee,
            period_month=date(2026, 10, 1),
            payment_date=date(2026, 10, 15),
            amount="250.00",
        )

        self.assertFalse(payment.is_approved)
        payment.approved_by = self.admin
        payment.save()
        self.assertTrue(payment.is_approved)

    def test_period_must_start_on_first_day(self):
        payment = PayrollPayment(
            employee=self.employee,
            period_month=date(2026, 10, 2),
            payment_date=date(2026, 10, 15),
            amount="250.00",
        )

        with self.assertRaises(ValidationError):
            payment.save()


class PayrollSummaryViewTest(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="summary-admin",
            password="password",
            is_staff=True,
        )
        employee_user = CustomUser.objects.create_user(
            username="summary-employee",
            password="password",
        )
        self.employee = Employee.objects.create(
            user=employee_user,
            employee_number="SUM001",
            hourly_rate="25.00",
            hired_on=date(2026, 1, 5),
        )
        WorkEntry.objects.create(
            employee=self.employee,
            work_date=date(2026, 10, 8),
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_minutes=60,
            status=WorkEntry.Status.APPROVED,
        )
        PayrollPayment.objects.create(
            employee=self.employee,
            period_month=date(2026, 10, 1),
            payment_date=date(2026, 10, 31),
            amount="50.00",
            approved_by=self.admin,
        )

    def test_staff_can_view_monthly_payroll_summary(self):
        self.client.force_login(self.admin)

        response = self.client.get("/hr/payroll/?year=2026&month=10")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "summary-employee")
        self.assertContains(response, "8.00")
        self.assertContains(response, "200.00")
        self.assertContains(response, "50.00")
        self.assertContains(response, "150.00")

    def test_staff_can_navigate_payroll_months(self):
        self.client.force_login(self.admin)

        response = self.client.get("/hr/payroll/?year=2026&month=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "year=2025&month=12")
        self.assertContains(response, "year=2026&month=2")

    def test_payments_are_counted_even_on_non_worked_days(self):
        PayrollPayment.objects.create(
            employee=self.employee,
            period_month=date(2026, 10, 1),
            payment_date=date(2026, 10, 20),
            amount="100.00",
            approved_by=self.admin,
        )
        self.client.force_login(self.admin)

        response = self.client.get("/hr/payroll/?year=2026&month=10")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "150.00")

    def test_non_staff_cannot_view_payroll_summary(self):
        self.client.force_login(self.employee.user)

        response = self.client.get("/hr/payroll/")

        self.assertEqual(response.status_code, 403)

    def test_staff_can_confirm_payment_from_summary(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            "/hr/payroll/",
            {
                "employee_id": self.employee.pk,
                "payment_date": "2026-10-08",
                "amount": "200.00",
                "notes": "October payment",
            },
        )

        self.assertRedirects(response, "/hr/payroll/?year=2026&month=10")
        payment = PayrollPayment.objects.get(
            employee=self.employee,
            payment_date=date(2026, 10, 8),
            notes="October payment",
        )
        self.assertEqual(payment.amount, 200)
        self.assertEqual(payment.approved_by, self.admin)
        self.assertIsNotNone(payment.approved_at)


class EmployeePayrollViewTest(TestCase):
    def setUp(self):
        self.employee_user = CustomUser.objects.create_user(
            username="my-payroll-employee",
            password="password",
        )
        self.other_user = CustomUser.objects.create_user(
            username="other-payroll-employee",
            password="password",
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            employee_number="MYPAY001",
            hourly_rate="25.00",
            hired_on=date(2026, 1, 5),
        )
        other_employee = Employee.objects.create(
            user=self.other_user,
            employee_number="MYPAY002",
            hourly_rate="50.00",
            hired_on=date(2026, 1, 5),
        )
        WorkEntry.objects.create(
            employee=self.employee,
            work_date=date(2026, 10, 8),
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_minutes=60,
            status=WorkEntry.Status.APPROVED,
        )
        PayrollPayment.objects.create(
            employee=self.employee,
            period_month=date(2026, 10, 1),
            payment_date=date(2026, 10, 15),
            amount="50.00",
            approved_by=self.other_user,
        )
        PayrollPayment.objects.create(
            employee=other_employee,
            period_month=date(2026, 10, 1),
            payment_date=date(2026, 10, 15),
            amount="999.00",
            approved_by=self.other_user,
        )

    def test_employee_sees_own_payroll(self):
        self.client.force_login(self.employee_user)

        response = self.client.get("/hr/my-payroll/?year=2026&month=10")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "25.00")
        self.assertContains(response, "50.00")
        self.assertContains(response, "200.00")
        self.assertContains(response, "150.00")
        self.assertNotContains(response, "999.00")

    def test_employee_can_navigate_payroll_months(self):
        self.client.force_login(self.employee_user)

        response = self.client.get("/hr/my-payroll/?year=2026&month=12")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "year=2026&month=11")
        self.assertContains(response, "year=2027&month=1")


class WorkEntryModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            username="w1", email="", password=""
        )
        self.employee = Employee.objects.create(
            user=self.user,
            employee_number="EMP001",
            hourly_rate="25.50",
            hired_on=date(2026, 1, 5),
        )

    def create_entry(self, **overrides):
        defaults = {
            "employee": self.employee,
            "work_date": date(2026, 10, 8),
            "start_time": time(8, 0),
            "end_time": time(17, 0),
            "break_minutes": 60,
        }
        defaults.update(overrides)
        return WorkEntry(**defaults)

    def test_work_entry_creation(self):
        entry = self.create_entry()
        entry.save()
        self.assertEqual(WorkEntry.objects.count(), 1)
        self.assertEqual(entry.status, WorkEntry.Status.DRAFT)
        self.assertEqual(entry.notes, "")
        self.assertIsNone(entry.approved_by)

    def test_break_defaults_to_thirty_minutes(self):
        entry = WorkEntry(
            employee=self.employee,
            work_date=date(2026, 10, 8),
            start_time=time(8, 0),
            end_time=time(17, 0),
        )

        self.assertEqual(entry.break_minutes, 30)

    def test_work_entry_str(self):
        entry = self.create_entry()
        entry.save()
        self.assertIn("EMP001", str(entry))
        self.assertIn("2026-10-08", str(entry))

    def test_duration_hours(self):
        entry = self.create_entry()
        entry.save()
        self.assertEqual(entry.duration_hours, 8.0)

    def test_duration_hours_no_break(self):
        entry = self.create_entry(break_minutes=0)
        entry.save()
        self.assertEqual(entry.duration_hours, 9.0)

    def test_duration_hours_rounded_to_two_decimals(self):
        # 08:00 - 09:45 = 1h45 without break = 1.75 h
        entry = self.create_entry(
            end_time=time(9, 45),
            break_minutes=0,
        )
        entry.save()
        self.assertEqual(entry.duration_hours, 1.75)

    def test_end_time_before_start_time_invalid(self):
        entry = self.create_entry(start_time=time(17, 0), end_time=time(8, 0))
        with self.assertRaises(ValidationError):
            entry.save()

    def test_end_time_equal_start_time_invalid(self):
        entry = self.create_entry(start_time=time(8, 0), end_time=time(8, 0))
        with self.assertRaises(ValidationError):
            entry.save()

    def test_break_longer_than_work_invalid(self):
        # 08:00 - 12:00 = 4 hours; a 240 minute break is longer
        entry = self.create_entry(
            end_time=time(12, 0),
            break_minutes=240,
        )
        with self.assertRaises(ValidationError):
            entry.save()

    def test_break_equal_to_work_invalid(self):
        entry = self.create_entry(
            end_time=time(9, 0),
            break_minutes=60,
        )
        with self.assertRaises(ValidationError):
            entry.save()

    def test_break_shorter_than_work_valid(self):
        entry = self.create_entry(
            end_time=time(12, 0),
            break_minutes=239,
        )
        entry.save()
        self.assertEqual(WorkEntry.objects.count(), 1)

    def test_unique_employee_date_start_time(self):
        self.create_entry().save()
        duplicate = self.create_entry(break_minutes=30)
        # unique_together violations surface as ValidationError here
        # because save() calls full_clean() first.
        with self.assertRaises(ValidationError):
            duplicate.save()

    def test_same_start_time_other_day_allowed(self):
        self.create_entry().save()
        other_day = self.create_entry(work_date=date(2026, 10, 9))
        other_day.save()
        self.assertEqual(WorkEntry.objects.count(), 2)

    def test_other_start_time_same_day_allowed(self):
        self.create_entry().save()
        other_slot = self.create_entry(start_time=time(18, 0), end_time=time(20, 0))
        other_slot.save()
        self.assertEqual(WorkEntry.objects.count(), 2)

    def test_status_choices(self):
        self.assertEqual(
            [s.value for s in WorkEntry.Status],
            ["draft", "approved", "rejected"],
        )

    def test_ordering_most_recent_first(self):
        oldest = self.create_entry(work_date=date(2026, 10, 1))
        oldest.save()
        newest = self.create_entry()
        newest.save()
        entries = WorkEntry.objects.all()
        self.assertIsInstance(entries, QuerySet)
        self.assertEqual(entries.first().pk, newest.pk)
        self.assertEqual(entries.last().pk, oldest.pk)
