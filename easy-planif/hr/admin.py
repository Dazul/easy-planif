from django.contrib import admin

from .models import Employee, PayrollPayment, WorkEntry


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_number",
        "user",
        "hourly_rate",
        "hired_on",
        "left_on",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("employee_number", "user__username")


@admin.register(WorkEntry)
class WorkEntryAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "work_date",
        "start_time",
        "end_time",
        "break_minutes",
        "status",
        "is_paid",
        "approved_by",
    )
    list_filter = ("status", "work_date")
    search_fields = ("employee__employee_number", "employee__user__username")
    date_hierarchy = "work_date"


@admin.register(PayrollPayment)
class PayrollPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "period_month",
        "payment_date",
        "amount",
        "work_entry",
        "approved_by",
        "approved_at",
    )
    list_filter = ("period_month", "payment_date")
    search_fields = ("employee__employee_number", "employee__user__username")
    date_hierarchy = "payment_date"
