import calendar
from datetime import datetime, timedelta, date
from django.http import HttpResponse, HttpResponseBadRequest
from django.views import generic
from django.utils.safestring import mark_safe

from .models import Event
from .utils import Calendar, GlobalCalendar
from .forms import EventForm

class CalendarView(generic.ListView):
    model = Event
    template_name = 'cal/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # use today's date for the calendar
        d = get_date(self.request.GET.get('month', None))

        # Instantiate our calendar class with today's year and date
        cal = Calendar(d.year, d.month)

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

def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split('-'))
        return date(year, month, day=1)
    return datetime.today()

def get_date_week(req_day):
    if req_day:
        year, month, day = (int(x) for x in req_day.split('-'))
        return date(year, month, day)
    return datetime.today()

def prev_month(m):
    first = m.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = 'month=' + str(prev_month.year) + '-' + str(prev_month.month)
    return month

def next_month(m):
    days_in_month = calendar.monthrange(m.year, m.month)[1]
    last = m.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = 'month=' + str(next_month.year) + '-' + str(next_month.month)
    return month

def prev_week(m):
    week_date = m - timedelta(days=7)
    week_date = 'week_date=' + str(week_date.year) + '-' + str(week_date.month) + '-' + str(week_date.day)
    return week_date

def next_week(m):
    week_date = m + timedelta(days=7)
    week_date = 'week_date=' + str(week_date.year) + '-' + str(week_date.month) + '-' + str(week_date.day)
    return week_date


def create_event(request, event_id=None):
    instance = Event()
    form = EventForm(request.POST or None, instance=instance)
    if request.POST and form.is_valid():
        form.save()
        return HttpResponse(status=201)
    return HttpResponseBadRequest()
