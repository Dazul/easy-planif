from django import forms

from .models import WorkEntry


class WorkEntryForm(forms.ModelForm):
    class Meta:
        model = WorkEntry
        fields = ["start_time", "end_time", "break_minutes", "notes"]
        widgets = {
            "start_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "end_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        }
