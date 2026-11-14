from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Employee


class HRView(View):

    def get(self, request):
        return render(request, 'hr.html')


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