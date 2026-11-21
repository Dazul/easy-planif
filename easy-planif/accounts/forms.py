from django.contrib.auth.forms import (
    AdminUserCreationForm,
    UserChangeForm,
    UserCreationForm,
)
from django import forms
from django.db import transaction
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from hr.models import Employee
from .models import CustomUser

class CustomUserCreationForm(AdminUserCreationForm):

    class Meta:
        model = CustomUser
        fields = ("username", "email")

class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = CustomUser
        fields = ("username", "email")


class UserEmployeeCreationForm(UserCreationForm):
    employee_number = forms.CharField(max_length=30)
    hourly_rate = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    hired_on = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    left_on = forms.DateField(
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = CustomUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        )

    def clean_employee_number(self):
        employee_number = self.cleaned_data["employee_number"]
        if Employee.objects.filter(employee_number=employee_number).exists():
            raise forms.ValidationError(
                "An employee with this number already exists."
            )
        return employee_number

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        employee = Employee(
            employee_number=cleaned_data["employee_number"],
            hourly_rate=cleaned_data["hourly_rate"],
            hired_on=cleaned_data["hired_on"],
            left_on=cleaned_data["left_on"],
            is_active=cleaned_data["is_active"],
        )
        try:
            employee.full_clean(exclude=["user"])
        except forms.ValidationError as error:
            self.add_error(None, error)
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        if Employee.objects.filter(
            employee_number=self.cleaned_data["employee_number"]
        ).exists():
            raise ValidationError(
                "An employee with this number already exists."
            )

        user = super().save(commit=False)
        user.must_change_password = True
        if commit:
            user.save()
            try:
                Employee.objects.create(
                    user=user,
                    employee_number=self.cleaned_data["employee_number"],
                    hourly_rate=self.cleaned_data["hourly_rate"],
                    hired_on=self.cleaned_data["hired_on"],
                    left_on=self.cleaned_data["left_on"],
                    is_active=self.cleaned_data["is_active"],
                )
            except IntegrityError as error:
                raise ValidationError(
                    "The user or employee could not be created."
                ) from error
        return user
