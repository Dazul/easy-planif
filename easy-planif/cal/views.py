from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.decorators import permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import generic
from django.utils.safestring import mark_safe
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .forms import EventForm
from .models import Event
from .utils import Calendar, GlobalCalendar, PlanningCalendar, ReplacementCalendar
from tasks.models import Tasks, Authorizations
from datetime import timedelta
from .helpers import get_date, prev_month, next_month, get_date_week, prev_week, next_week

class CalendarView(generic.ListView):
    model = Event
    template_name = 'cal/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # use today's date for the calendar
        d = get_date(self.request.GET.get('month', None))

        # Instantiate our calendar class with today's year and date
        cal = Calendar(self.request.user, d.year, d.month)

        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatmonth(withyear=True)
        context['calendar'] = mark_safe(html_cal)

        context['prev_month'] = prev_month(d)
        context['next_month'] = next_month(d)

        return context

class GlobalCalendarView(generic.ListView):
    model = Event
    template_name = 'cal/global_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # use today's date for the calendar
        today = get_date_week(self.request.GET.get('week_date', None))
        monday = today - timedelta(days=today.weekday())

        week_dates = [monday + timedelta(days=i) for i in range(7)]

        cal = GlobalCalendar()
        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatweek(week_dates)
        context['calendar'] = mark_safe(html_cal)

        context['prev_week'] = prev_week(today)
        context['next_week'] = next_week(today)

        return context

class ReplacementCalendarView(generic.ListView):
    model = Event
    template_name = 'cal/replacements.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # use today's date for the calendar
        today = get_date_week(self.request.GET.get('week_date', None))
        monday = today - timedelta(days=today.weekday())

        week_dates = [monday + timedelta(days=i) for i in range(7)]

        cal = ReplacementCalendar(self.request.user)
        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatweek(week_dates)
        context['replacements'] = mark_safe(html_cal)

        context['prev_week'] = prev_week(today)
        context['next_week'] = next_week(today)

        return context

class PlanningView(PermissionRequiredMixin, generic.ListView):
    model = Event
    template_name = 'cal/planning.html'
    permission_required = 'cal.assign_task'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # use today's date for the calendar
        today = get_date_week(self.request.GET.get('week_date', None))
        monday = today - timedelta(days=today.weekday())

        week_dates = [monday + timedelta(days=i) for i in range(7)]

        tasks = Tasks.objects.all()

        cal = PlanningCalendar()
        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatweek(week_dates,  context['view'].request)
        context['calendar'] = mark_safe(html_cal)
        context['tasks'] = tasks
        context['prev_week'] = prev_week(today)
        context['next_week'] = next_week(today)

        return context

def replace(request):
    event = Event.objects.filter(id=request.GET.get('event_id'))[0]
    event.user = request.user
    event.is_replaceable = False
    event.save()
    return HttpResponseRedirect("/")

def create_event(request):
    instance = Event()
    form = EventForm(request.POST or None, instance=instance)
    if request.POST and form.is_valid():
        event = form.save(commit=False)
        event.user = request.user
        event.save()
        return HttpResponse(status=201)
    return HttpResponseBadRequest()

@permission_required('cal.assign_task', raise_exception=True)
def update_event(request):
    event = Event.objects.filter(id=request.POST.get('event_id'))[0]
    event.is_available = False
    event.tasks = Tasks.objects.filter(id=request.POST.get('task_id'))[0]
    event.save()
    return_path = "/planning"
    has_week_date = False
    if request.POST['week_date'] != 'None':
        return_path += '?week_date=' + request.POST['week_date']
        has_week_date = True
    if request.POST['task'] != 'None':
        if has_week_date:
            return_path += '&task=' + request.POST['task']
        else:
            return_path += '?task=' + request.POST['task']
    return HttpResponseRedirect(return_path)

def toggle_replacement(request):
    event = Event.objects.filter(id=request.GET.get('event_id'))[0]
    if event.user == request.user and not event.is_available:
        event.is_replaceable = not event.is_replaceable
        event.save()
        return HttpResponseRedirect("/calendar")
    return HttpResponseForbidden()