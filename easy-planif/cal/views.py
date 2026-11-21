from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse
from django.contrib.auth.decorators import permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import generic
from django.utils.safestring import mark_safe
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .forms import EventForm, AddBookingForm, AddBookingTypeForm
from .models import Event, Booking, BookingType, ReplacementRequest
from .utils import Calendar, GlobalCalendar, PlanningCalendar, ReplacementCalendar, BookingsCalendar
from tasks.models import Tasks, Authorizations
from datetime import timedelta
from .helpers import get_date, prev_month, next_month, get_date_week, prev_week, next_week

class CalendarView(generic.ListView):
    model = Event
    template_name = 'cal/calendar.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

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

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

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

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

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

@login_required
def replace(request):
    """Register interest in taking a replaceable event.

    Creates a pending ReplacementRequest instead of taking the event
    directly; an HR staff member then validates or refuses it (the
    validation applies the actual user swap).
    """
    event = get_object_or_404(Event, id=request.GET.get("event_id"))
    if event.user == request.user:
        return HttpResponseForbidden("You cannot replace yourself.")
    if not event.is_replaceable:
        return HttpResponseForbidden("This event is not replaceable.")
    if not Authorizations.objects.filter(
        user=request.user, task=event.tasks
    ).exists():
        return HttpResponseForbidden("You are not authorized for this task.")
    # already requested by this user?
    if ReplacementRequest.objects.filter(
        event=event, replacement_user=request.user, status=ReplacementRequest.Status.PENDING
    ).exists():
        return HttpResponseRedirect(reverse("cal:replacements"))
    # someone else already has a pending request on this event?
    if ReplacementRequest.objects.filter(
        event=event, status=ReplacementRequest.Status.PENDING
    ).exists():
        return HttpResponseForbidden("Someone already requested this replacement.")
    ReplacementRequest.objects.create(
        event=event, replacement_user=request.user
    )
    return HttpResponseRedirect(reverse("cal:replacements"))

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
    event.is_if_needed = False
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

def toggle_if_needed(request):
    event = Event.objects.filter(id=request.GET.get('event_id'))[0]
    if event.user == request.user and event.is_available:
        # cycle: available -> available if needed -> removed
        if event.is_if_needed:
            event.delete()
        else:
            event.is_if_needed = True
            event.save()
        return HttpResponseRedirect("/calendar")
    return HttpResponseForbidden()
class BookingsView(PermissionRequiredMixin, generic.ListView):
    model = Booking
    template_name = 'cal/bookings.html'
    permission_required = 'cal.bookings_view'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # use today's date for the calendar
        d = get_date(self.request.GET.get('month', None))

        # Instantiate our calendar class with today's year and date
        cal = BookingsCalendar(d.year, d.month)

        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatmonth(withyear=True)
        context['bookings'] = mark_safe(html_cal)

        context['prev_month'] = prev_month(d)
        context['next_month'] = next_month(d)

        return context

@permission_required('cal.bookings_manager', raise_exception=True)
def add_booking(request):
    if request.method == "POST":
        form = AddBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.last_author = request.user
            booking.save()
            return HttpResponseRedirect("/bookings")
    else:
        form = AddBookingForm()
    return render(request, "cal/add_booking.html", {"form": form})

class BookingTypeView(generic.ListView):
    model = BookingType
    template_name = 'cal/booking_type.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = '<ul class="list-group">'
        for t in BookingType.objects.all():
            color = f' <span style="color:{t.color};">&#9632;</span>' if t.color else ''
            d += f'<li class="list-group-item"> {t.booking_type} {color} </li>'
        d += '</ul>'
        context['booking_types'] = mark_safe(d)
        return context

@staff_member_required
def add_booking_type(request):
    if request.method == "POST":
        form = AddBookingTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/bookingTypes")
    else:
        form = AddBookingTypeForm()
    return render(request, "cal/add_booking_type.html", {"form": form})

class BookingDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Booking
    template_name = 'cal/booking_detail.html'
    permission_required = 'cal.bookings_view'
    raise_exception = True
    context_object_name = 'booking'

@permission_required('cal.bookings_manager', raise_exception=True)
def edit_booking(request, pk):
    booking = Booking.objects.get(pk=pk)
    if request.method == "POST":
        form = AddBookingForm(request.POST, instance=booking)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.last_author = request.user
            booking.save()
            return HttpResponseRedirect(
                reverse("cal:booking_detail", args=[booking.id])
            )
    else:
        form = AddBookingForm(instance=booking)
    return render(request, "cal/booking_edit.html", {"form": form})

class BookingDayView(PermissionRequiredMixin, generic.ListView):
    model = Booking
    template_name = 'cal/booking_day.html'
    permission_required = 'cal.bookings_view'
    raise_exception = True
    context_object_name = 'bookings_list'

    def get_queryset(self):
        day = self.kwargs['day']
        qs = Booking.objects.filter(date=day).order_by('hour_start')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['day'] = self.kwargs['day']
        return context
