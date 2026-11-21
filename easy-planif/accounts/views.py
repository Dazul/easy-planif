from django.views import generic
from django.utils.safestring import mark_safe
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from .forms import UserEmployeeCreationForm
from .models import CustomUser
# Create your views here.


class RequiredPasswordChangeView(PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.must_change_password = False
        self.request.user.save(update_fields=["must_change_password"])
        return response


class RequiredPasswordChangeDoneView(TemplateView):
    template_name = "registration/password_change_done.html"

class UsersView(generic.ListView):
    model = CustomUser
    template_name = 'users.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = '<ul class="list-group">'
        for m in CustomUser.objects.all():
            d += f'<li class="list-group-item"> {m.username} </li>'
        d += '</ul>'
        context['users'] = mark_safe(d)
        context["user_creation_form"] = kwargs.get(
            "user_creation_form",
            UserEmployeeCreationForm(),
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        form = UserEmployeeCreationForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                return redirect("users")
        context = self.get_context_data(
            object_list=self.get_queryset(),
            user_creation_form=form,
        )
        return self.render_to_response(context, status=400)
