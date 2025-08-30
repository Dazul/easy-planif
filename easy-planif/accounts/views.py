from django.views import generic
from django.utils.safestring import mark_safe

from .models import CustomUser
# Create your views here.

class UsersView(generic.ListView):
    model = CustomUser
    template_name = 'users.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = ''
        for m in CustomUser.objects.all():
            d += f'<li> {m.username} </li>'
        context['users'] = mark_safe(d)
        return context
