from datetime import date, time

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.test import TestCase

from accounts.models import CustomUser

from .models import Employee, WorkEntry


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
        self.assertIsNone(employee.monthly_salary)

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
