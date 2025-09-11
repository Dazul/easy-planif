from django.views import generic
from django.utils.safestring import mark_safe

from .models import CustomUser
# Create your views here.

class UsersView(generic.ListView):
    model = CustomUser
    template_name = 'users.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = '<ul class="list-group">'
        for m in CustomUser.objects.all():
            d += f'<li class="list-group-item"> {m.username} </li>'
        d += '</ul>'
        context['users'] = mark_safe(d)
        return context
