from django.views import generic
from django.utils.safestring import mark_safe
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import CustomUser
# Create your views here.

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
        return context
