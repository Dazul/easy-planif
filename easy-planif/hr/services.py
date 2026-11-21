import calendar
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils.timezone import now

from .models import Employee, PayrollPayment, WorkEntry


ZERO = Decimal("0.00")


def normalize_month(year, month, default_year, default_month):
    if month not in range(1, 13):
        return default_year, default_month
    return year, month


def month_navigation(year, month, offset):
    month += offset
    if month == 0:
        return year - 1, 12
    if month == 13:
        return year + 1, 1
    return year, month


def work_entry_due(entry):
    return (entry.duration_hours * entry.employee.hourly_rate).quantize(
        Decimal("0.01")
    )


@transaction.atomic
def pay_work_entry(*, employee, entry_id, amount, payment_date, approved_by, notes=""):
    entry = (
        WorkEntry.objects.select_for_update()
        .select_related("employee", "employee__user")
        .get(
            pk=entry_id,
            employee=employee,
            status=WorkEntry.Status.APPROVED,
        )
    )
    if entry.is_paid:
        raise ValueError("This work entry is already paid.")

    due = work_entry_due(entry)
    if amount < due:
        raise ValueError(
            f"Payment amount cannot be below the due amount of {due}."
        )

    period_month = date(payment_date.year, payment_date.month, 1)
    payment = PayrollPayment.objects.create(
        employee=employee,
        period_month=period_month,
        payment_date=payment_date,
        amount=amount,
        notes=notes,
        approved_by=approved_by,
        approved_at=now(),
        work_entry=entry,
    )
    entry.is_paid = True
    entry.save(update_fields=["is_paid"])
    return payment


def build_payroll_summary(year, month, selected_employee=None):
    period_month = date(year, month, 1)
    entries = WorkEntry.objects.filter(
        work_date__year=year,
        work_date__month=month,
        status=WorkEntry.Status.APPROVED,
    ).select_related(
        "employee",
        "employee__user",
        "payroll_payment",
    )
    if selected_employee is not None:
        entries = entries.filter(employee=selected_employee)

    rows = []
    for entry in entries:
        due = work_entry_due(entry)
        payment = getattr(entry, "payroll_payment", None)
        rows.append(
            {
                "entry": entry,
                "date": entry.work_date,
                "employee": entry.employee,
                "hours": entry.duration_hours,
                "due": due,
                "paid": payment.amount if payment is not None else ZERO,
            }
        )

    rows.sort(
        key=lambda row: (
            row["date"],
            row["employee"].employee_number,
            row["entry"].start_time,
        )
    )
    total_hours = sum((row["hours"] for row in rows), ZERO)
    total_due = sum((row["due"] for row in rows), ZERO)
    total_paid = sum((row["paid"] for row in rows), ZERO)

    legacy_payments = PayrollPayment.objects.filter(
        period_month=period_month,
        work_entry__isnull=True,
        approved_by__isnull=False,
    )
    if selected_employee is not None:
        legacy_payments = legacy_payments.filter(employee=selected_employee)
    total_paid += sum(
        (payment.amount for payment in legacy_payments),
        ZERO,
    )

    return {
        "period_month": period_month,
        "rows": rows,
        "total_hours": total_hours,
        "total_due": total_due,
        "total_paid": total_paid,
        "total_remaining": max(total_due - total_paid, ZERO),
    }


def build_month_calendar(year, month, entries_by_date, today):
    month_calendar = calendar.Calendar(firstweekday=0)
    weeks = [
        [
            {
                "date": day,
                "entries": entries_by_date.get(day, []),
                "is_current_month": day.month == month,
                "day_state": (
                    "past"
                    if day < today
                    else "today"
                    if day == today
                    else "future"
                ),
            }
            for day in week
        ]
        for week in month_calendar.monthdatescalendar(year, month)
    ]
    visible_weeks = month_calendar.monthdatescalendar(year, month)
    return month_calendar, visible_weeks, weeks
