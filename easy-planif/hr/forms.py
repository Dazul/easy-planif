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


class WorkEntryCreateForm(forms.ModelForm):
    break_minutes = forms.IntegerField(
        required=False,
        min_value=0,
        initial=30,
    )

    class Meta:
        model = WorkEntry
        fields = ["employee", "start_time", "end_time", "break_minutes", "notes"]
        widgets = {
            "start_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "end_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        }

    def clean_break_minutes(self):
        return self.cleaned_data["break_minutes"] or 30

