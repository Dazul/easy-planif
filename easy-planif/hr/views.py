import calendar
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.timezone import localdate, now
from django.views import View

from .forms import EmployeeForm, WorkEntryCreateForm, WorkEntryForm
from .models import Employee, PayrollPayment, WorkEntry


class HRView(View):

    def get(self, request):
        return render(request, "hr.html")


class EmployeeListView(View):
    template_name = "hr.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        employees = Employee.objects.select_related("user").all()
        return render(
            request,
            self.template_name,
            {
                "employees": employees,
                "show_employee_list": True,
            },
        )


class EmployeeCreateView(View):
    template_name = "hr.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "show_employee_form": True,
                "employee_form": EmployeeForm(),
            },
        )

    def post(self, request):
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("hr:employee_list")
        return render(
            request,
            self.template_name,
            {
                "show_employee_form": True,
                "employee_form": form,
            },
            status=400,
        )


class PayrollSummaryView(View):
    template_name = "hr.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return self.render_summary(request)

    def post(self, request):
        employee = get_object_or_404(
            Employee,
            pk=request.POST.get("employee_id"),
        )
        try:
            payment_date = date.fromisoformat(request.POST["payment_date"])
            amount = Decimal(request.POST["amount"])
        except (KeyError, TypeError, ValueError, ArithmeticError):
            raise PermissionDenied("Invalid payroll payment data.")

        period_month = date(payment_date.year, payment_date.month, 1)
        PayrollPayment.objects.create(
            employee=employee,
            period_month=period_month,
            payment_date=payment_date,
            amount=amount,
            notes=request.POST.get("notes", ""),
            approved_by=request.user,
            approved_at=now(),
        )
        return redirect(
            f"{request.path}?year={period_month.year}&month={period_month.month}"
        )

    def render_summary(self, request):
        today = localdate()
        year = self._get_month_value(request, "year", today.year)
        month = self._get_month_value(request, "month", today.month)
        if month not in range(1, 13):
            year, month = today.year, today.month

        period_month = date(year, month, 1)
        entries = WorkEntry.objects.filter(
            work_date__year=year,
            work_date__month=month,
            status=WorkEntry.Status.APPROVED,
        ).select_related("employee", "employee__user")
        payments = PayrollPayment.objects.filter(
            period_month=period_month,
            approved_by__isnull=False,
        ).select_related("employee", "employee__user")

        rows_by_employee_date = {}
        for entry in entries:
            key = (entry.employee_id, entry.work_date)
            row = rows_by_employee_date.setdefault(
                key,
                {
                    "date": entry.work_date,
                    "employee": entry.employee,
                    "hours": Decimal("0.00"),
                    "due": Decimal("0.00"),
                    "paid": Decimal("0.00"),
                },
            )
            row["hours"] += entry.duration_hours
            row["due"] += (
                entry.duration_hours * entry.employee.hourly_rate
            ).quantize(Decimal("0.01"))

        payments_by_employee = {}
        for payment in payments:
            payments_by_employee[payment.employee_id] = (
                payments_by_employee.get(payment.employee_id, Decimal("0.00"))
                + payment.amount
            )

        for row in rows_by_employee_date.values():
            row["paid"] = payments_by_employee.get(
                row["employee"].pk,
                Decimal("0.00"),
            )

        rows = sorted(
            rows_by_employee_date.values(),
            key=lambda row: (row["date"], row["employee"].employee_number),
        )
        total_hours = sum((row["hours"] for row in rows), Decimal("0.00"))
        total_due = sum((row["due"] for row in rows), Decimal("0.00"))
        total_paid = sum((row["paid"] for row in rows), Decimal("0.00"))

        return render(
            request,
            self.template_name,
            {
                "show_payroll_summary": True,
                "payroll_month": period_month,
                "payroll_previous": self._month_navigation(year, month, -1),
                "payroll_next": self._month_navigation(year, month, 1),
                "payroll_rows": rows,
                "payroll_total_hours": total_hours,
                "payroll_total_due": total_due,
                "payroll_total_paid": total_paid,
                "payroll_balance": total_due - total_paid,
            },
        )

    @staticmethod
    def _month_navigation(year, month, offset):
        month += offset
        if month == 0:
            return year - 1, 12
        if month == 13:
            return year + 1, 1
        return year, month

    @staticmethod
    def _get_month_value(request, name, default):
        try:
            return int(request.GET.get(name, default))
        except (TypeError, ValueError):
            return default


class EmployeePayrollView(View):
    template_name = "hr.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        employee = get_object_or_404(
            Employee.objects.select_related("user"),
            user=request.user,
        )
        today = localdate()
        year = self._get_month_value(request, "year", today.year)
        month = self._get_month_value(request, "month", today.month)
        if month not in range(1, 13):
            year, month = today.year, today.month

        period_month = date(year, month, 1)
        entries = WorkEntry.objects.filter(
            employee=employee,
            work_date__year=year,
            work_date__month=month,
            status=WorkEntry.Status.APPROVED,
        )
        payments = PayrollPayment.objects.filter(
            employee=employee,
            period_month=period_month,
            approved_by__isnull=False,
        )
        total_hours = sum(
            (entry.duration_hours for entry in entries),
            Decimal("0.00"),
        )
        total_due = (total_hours * employee.hourly_rate).quantize(
            Decimal("0.01")
        )
        total_paid = sum(
            (payment.amount for payment in payments),
            Decimal("0.00"),
        )

        return render(
            request,
            self.template_name,
            {
                "show_employee_payroll": True,
                "employee_payroll_month": period_month,
                "employee_payroll_previous": self._month_navigation(
                    year, month, -1
                ),
                "employee_payroll_next": self._month_navigation(
                    year, month, 1
                ),
                "employee_hourly_rate": employee.hourly_rate,
                "employee_payments": payments,
                "employee_total_hours": total_hours,
                "employee_total_due": total_due,
                "employee_total_paid": total_paid,
                "employee_balance": total_due - total_paid,
            },
        )

    @staticmethod
    def _month_navigation(year, month, offset):
        month += offset
        if month == 0:
            return year - 1, 12
        if month == 13:
            return year + 1, 1
        return year, month

    @staticmethod
    def _get_month_value(request, name, default):
        try:
            return int(request.GET.get(name, default))
        except (TypeError, ValueError):
            return default


class WorkCalendarView(View):
    template_name = "hr.html"
    employee_only = False

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        today = localdate()
        year = self._get_month_value(request, "year", today.year)
        month = self._get_month_value(request, "month", today.month)
        if month not in range(1, 13):
            year, month = today.year, today.month

        first_day = date(year, month, 1)
        entries = self.get_entries_queryset(request).filter(
            work_date__year=year,
            work_date__month=month,
        ).select_related("employee", "employee__user")
        entries_by_date = {}
        for entry in entries:
            entries_by_date.setdefault(entry.work_date, []).append(entry)

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

        previous_month = month - 1
        previous_year = year
        if previous_month == 0:
            previous_month, previous_year = 12, year - 1
        next_month = month + 1
        next_year = year
        if next_month == 13:
            next_month, next_year = 1, year + 1

        return render(
            request,
            self.template_name,
            {
                "show_work_calendar": True,
                "employee_calendar": self.employee_only,
                "calendar_weeks": weeks,
                "calendar_month": first_day,
                "previous_year": previous_year,
                "previous_month": previous_month,
                "next_year": next_year,
                "next_month": next_month,
            },
        )

    def get_entries_queryset(self, request):
        return WorkEntry.objects.all()

    @staticmethod
    def _get_month_value(request, name, default):
        try:
            return int(request.GET.get(name, default))
        except (TypeError, ValueError):
            return default


class WorkDayView(View):
    template_name = "hr.html"
    employee_only = False

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, work_date):
        entries = self.get_entries_queryset(request).filter(
            work_date=work_date,
        ).select_related("employee", "employee__user")
        entry_rows = [
            {
                "entry": entry,
                "form": self._entry_form(entry),
                "form_id": f"entry-form-{entry.pk}",
            }
            for entry in entries
        ]
        return render(
            request,
            self.template_name,
            {
                "show_work_day": True,
                "employee_day": self.employee_only,
                "work_date": work_date,
                "work_entries": entries,
                "entry_rows": entry_rows,
                "new_entry_form": (
                    WorkEntryCreateForm() if not self.employee_only else None
                ),
            },
        )

    def post(self, request, work_date):
        parsed_work_date = date.fromisoformat(work_date)
        if not request.POST.get("entry_id"):
            form = WorkEntryCreateForm(
                request.POST,
                instance=WorkEntry(work_date=parsed_work_date),
            )
            if form.is_valid():
                entry = form.save(commit=False)
                entry.work_date = parsed_work_date
                entry.save()
                return redirect("hr:work_day", work_date=work_date)
            return render(
                request,
                self.template_name,
                {
                    "show_work_day": True,
                    "employee_day": self.employee_only,
                    "work_date": work_date,
                    "work_entries": self.get_entries_queryset(request).filter(
                        work_date=work_date,
                    ),
                    "entry_rows": [],
                    "new_entry_form": form,
                },
                status=400,
            )

        entry = get_object_or_404(
            self.get_entries_queryset(request),
            pk=request.POST.get("entry_id"),
            work_date=work_date,
        )
        if (
            request.POST.get("action", "approve") == "approve"
            and "start_time" not in request.POST
        ):
            entry.status = WorkEntry.Status.APPROVED
            entry.approved_by = request.user
            entry.save()
            return redirect("hr:work_day", work_date=work_date)

        form = WorkEntryForm(request.POST, instance=entry)
        if not form.is_valid():
            for field in form.fields.values():
                field.widget.attrs["form"] = f"entry-form-{entry.pk}"
            entries = self.get_entries_queryset(request).filter(
                work_date=work_date,
            ).select_related("employee", "employee__user")
            entry_rows = [
                {
                    "entry": current_entry,
                    "form": (
                        form
                        if current_entry.pk == entry.pk
                        else self._entry_form(current_entry)
                    ),
                    "form_id": f"entry-form-{current_entry.pk}",
                }
                for current_entry in entries
            ]
            return render(
                request,
                self.template_name,
                {
                    "show_work_day": True,
                    "employee_day": self.employee_only,
                    "work_date": work_date,
                    "work_entries": entries,
                    "entry_rows": entry_rows,
                },
                status=400,
            )

        entry = form.save(commit=False)
        if request.POST.get("action") == "approve":
            entry.status = WorkEntry.Status.APPROVED
            entry.approved_by = request.user
        entry.save()
        return redirect("hr:work_day", work_date=work_date)

    @staticmethod
    def _entry_form(entry):
        form = WorkEntryForm(instance=entry)
        for field in form.fields.values():
            field.widget.attrs["form"] = f"entry-form-{entry.pk}"
        return form

    def get_entries_queryset(self, request):
        return WorkEntry.objects.all()


class EmployeeWorkCalendarView(WorkCalendarView):
    employee_only = True

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return View.dispatch(self, request, *args, **kwargs)

    def get_entries_queryset(self, request):
        return WorkEntry.objects.filter(employee__user=request.user)

class EmployeeWorkDayView(WorkDayView):
    employee_only = True

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return View.dispatch(self, request, *args, **kwargs)

    def get_entries_queryset(self, request):
        return WorkEntry.objects.filter(employee__user=request.user)

    def post(self, request, work_date):
        raise PermissionDenied("Employees cannot approve work entries.")
