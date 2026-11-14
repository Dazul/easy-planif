import calendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.timezone import localdate
from django.views import View

from .models import Employee, WorkEntry


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


class WorkCalendarView(View):
    template_name = "hr.html"

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
        entries = WorkEntry.objects.filter(
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
                "calendar_weeks": weeks,
                "calendar_month": first_day,
                "previous_year": previous_year,
                "previous_month": previous_month,
                "next_year": next_year,
                "next_month": next_month,
            },
        )

    @staticmethod
    def _get_month_value(request, name, default):
        try:
            return int(request.GET.get(name, default))
        except (TypeError, ValueError):
            return default


class WorkDayView(View):
    template_name = "hr.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, work_date):
        entries = WorkEntry.objects.filter(
            work_date=work_date,
        ).select_related("employee", "employee__user")
        return render(
            request,
            self.template_name,
            {
                "show_work_day": True,
                "work_date": work_date,
                "work_entries": entries,
            },
        )

    def post(self, request, work_date):
        entry = get_object_or_404(
            WorkEntry,
            pk=request.POST.get("entry_id"),
            work_date=work_date,
        )
        entry.status = WorkEntry.Status.APPROVED
        entry.approved_by = request.user
        entry.save()
        return redirect("hr:work_day", work_date=work_date)
