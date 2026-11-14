from django import forms

from accounts.models import CustomUser

from .models import Employee, WorkEntry


class WorkEntryForm(forms.ModelForm):
    class Meta:
        model = WorkEntry
        fields = ["start_time", "end_time", "break_minutes", "notes"]
        widgets = {
            "start_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "end_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        }


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "user",
            "employee_number",
            "hourly_rate",
            "hired_on",
            "left_on",
            "is_active",
        ]
        widgets = {
            "hired_on": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "left_on": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = CustomUser.objects.filter(
            employee_profile__isnull=True,
        ).order_by("username")
