from calendar import HTMLCalendar

from tasks.models import Tasks, Authorizations
from accounts.models import CustomUser
from .models import Event, Booking, ReplacementRequest
from django.template.loader import render_to_string

class Calendar(HTMLCalendar):
    def __init__(self, current_user=None, year=None, month=None):
        self.year = year
        self.month = month
        self.current_user = current_user
        super().__init__()

    # formats a day as a td
    # filter events by day
    def formatday(self, day, events):
        events_per_day = events.filter(date__day=day)
        d = ''
        event_found = False
        for event in events_per_day:
            if event.user == self.current_user:
                event_found = True
                if event.is_available:
                    label = "Available" + (" (if needed)" if event.is_if_needed else "")
                    d += f'<li> <a href="toggle_if_needed?event_id={event.id}">{label}</a> </li>'
                else:
                    rep = "(R)" if event.is_replaceable else ""
                    d += f'<li> <a href="toggle_replacement?event_id={event.id}">{event.tasks} {rep}</a> </li>'
        if day == 0:
            return '<td></td>'
        if not event_found:
            # whole cell is clickable to create a standard availability
            return (
                f"<td class='free-day' onclick=\"createAvailableEvent('{day}-{self.month}-{self.year}')\">"
                f"<span class='date'>{day}</span><ul> {d} </ul></td>"
            )
        return f"<td><span class='date'>{day}</span><ul> {d} </ul></td>"

    # formats a week as a tr
    def formatweek(self, theweek, events):
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, events)
        return f'<tr> {week} </tr>'

    # formats a month as a table
    # filter events by year and month
    def formatmonth(self, withyear=True):
        events = Event.objects.filter(date__year=self.year, date__month=self.month)

        cal = '<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'{self.formatweekheader()}\n'
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f'{self.formatweek(week, events)}\n'
        cal += '</table>'
        return cal

class GlobalCalendar(Calendar):
    def __init__(self):
        super().__init__()

    def formatday(self, day, events, user_id):
        events_per_day = events.filter(date__day=day, user__id=user_id)
        d = ''
        if len(events_per_day) != 0:
            for event in events_per_day:
                if event.is_available:
                    label = "Available" + (" (if needed)" if event.is_if_needed else "")
                    d += f'<li> {label} </li>'
                else:
                    d += f'<li> {event.tasks} </li>'
        return f'<td style="height:30px;"><ul> {d} </ul></td>'

    def weekheader(self, theweek):
        w = '<tr><th>User</th>'
        for day in theweek:
            w += f'<th>{day.strftime("%Y-%m-%d")}</th>'
        w += '</tr>'
        return w

    # formats a week as a tr
    def formatweek(self, theweek):
        events = Event.objects.filter(date__gte=theweek[0], date__lte=theweek[6])
        week = '<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        week += self.weekheader(theweek)
        users = {}
        for event in events:
            if event.user.id not in users.keys():
                users[event.user.id] = event.user
        for uid, user in users.items():
            week += f'<tr><td style="height:30px;">{user}</td>'
            for d in theweek:
                week += self.formatday(d.day, events, uid)
            week += '</tr>'
        return week

class ReplacementCalendar(Calendar):
    def __init__(self, current_user, week_date=None):
        super().__init__(current_user)
        # anchor date of the displayed week, so actions can send the
        # user back to the same week (and not the real current one)
        self.week_date = week_date

    def formatday(self, day, events, user_id):
        events_per_day = events.filter(date__day=day, user__id=user_id)
        d = ''
        if len(events_per_day) != 0:
            for event in events_per_day:
                pending = ReplacementRequest.objects.filter(
                    event=event, status=ReplacementRequest.Status.PENDING
                ).first()
                if pending:
                    # waiting for HR validation: not takeable anymore
                    d += (
                        f'<li> {event.tasks} '
                        f'(requested by {pending.replacement_user})</li>'
                    )
                elif Authorizations.objects.filter(user_id=self.current_user, task_id=event.tasks_id).exists():
                    link = f"replacements/replace?event_id={event.id}"
                    if self.week_date:
                        link += f"&week_date={self.week_date}"
                    d += f'<li>  <a href="{link}">{event.tasks}</a></li>'
                else:
                    d += f'<li> {event.tasks} </li>'
        return f'<td class="day"><ul> {d} </ul></td>'

    def weekheader(self, theweek):
        w = '<tr><th>User</th>'
        for day in theweek:
            w += f'<th>{day.strftime("%Y-%m-%d")}</th>'
        w += '</tr>'
        return w

    # formats a week as a tr
    def formatweek(self, theweek):
        events = Event.objects.filter(date__gte=theweek[0], date__lte=theweek[6], is_replaceable=True)
        week = '<table border="0" cellpadding="0" cellspacing="0" class="calendar replacements">\n'
        week += self.weekheader(theweek)
        users = {}
        for event in events:
            if event.user.id not in users.keys():
                users[event.user.id] = event.user
        for uid, user in users.items():
            week += f'<tr><td class="user-label">{user}</td>'
            for d in theweek:
                week += self.formatday(d.day, events, uid)
            week += '</tr>'
        return week

class PlanningCalendar(GlobalCalendar):
    def __init__(self):
        super().__init__()

    def define_form(self, event_id, request):
        user = CustomUser.objects.get(id=Event.objects.get(id=event_id).user_id)
        auths = Authorizations.objects.all().filter(user=user)
        week_date = request.GET.get('week_date')
        selected_task_id = request.GET.get('task')
        context = {'event_id': event_id, 'week_date': week_date}
        if selected_task_id is not None:
            # A task is chosen in the header: replace the dropdown with a
            # one-click quick-assign box for that task.
            for auth in auths:
                if str(auth.task_id) == selected_task_id:
                    context['task'] = Tasks.objects.get(id=auth.task_id)
                    return render_to_string(
                        "cal/quick_assign.html", context, request=request
                    )
            # Selected task is not among the user's authorized tasks
            return '---'
        context['tasks'] = [Tasks.objects.get(id=auth.task_id) for auth in auths]
        return render_to_string(
            "cal/dropdown_planning.html", context, request=request
        )

    def formatday(self, day, events, user_id, request):
        events_per_day = events.filter(date__day=day, user__id=user_id)
        d = ''
        pre = ''
        if len(events_per_day) != 0:
            for event in events_per_day:
                if event.is_available:
                    if event.is_if_needed:
                        d += '<li class="if-needed-info"> If needed </li>'
                    rendered = self.define_form(event.id, request)
                    if '<form' in rendered:
                        # a quick-assign button renders outside the ul,
                        # otherwise its text overflows the button
                        pre += rendered
                    else:
                        d += rendered
                else:
                    d += f'<li> {event.tasks} </li>'
        return f'<td style="height:30px;">{pre}<ul> {d} </ul></td>'

    @staticmethod
    def user_stats(user, month_date):
        """
        Return "(assigned days)/(bookable days)" for the calendar month
        of month_date, where bookable days are days with an availability
        (standard or if needed) or an assigned task.
        """
        assigned = 0
        bookable = 0
        events = Event.objects.filter(
            user=user,
            date__year=month_date.year,
            date__month=month_date.month,
        )
        for event in events:
            bookable += 1
            if not event.is_available:
                assigned += 1
        if bookable == 0:
            return ""
        return f"{assigned}/{bookable}"

    def formatweek(self, theweek, request):
        events = Event.objects.filter(date__gte=theweek[0], date__lte=theweek[6])
        week = '<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        week += self.weekheader(theweek)
        users = {}
        for event in events:
            if event.user.id not in users.keys():
                users[event.user.id] = event.user
        for uid, user in users.items():
            stats = self.user_stats(user, theweek[0])
            name_cell = f"{user}"
            if stats:
                name_cell += f' <span class="user-stats">({stats})</span>'
            week += f'<tr><td style="height:30px;">{name_cell}</td>'
            for d in theweek:
                week += self.formatday(d.day, events, uid, request)
            week += '</tr>'
        return week

class BookingsCalendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super().__init__()

    # formats a day as a td
    # filter bookings by day
    def formatday(self, day, bookings):
        bookings_per_day = bookings.filter(date__day=day)
        d = ''
        for booking in bookings_per_day:
            # color code per booking type as entry background (issue #36)
            if booking.booking_type and booking.booking_type.color:
                color = booking.booking_type.color
                entry_style = f'background-color: {color};'
            else:
                entry_style = 'background-color: #eeeeee;'
            rep = ''
            if booking.date_report:
                rep = f' (report: {booking.date_report})'
            d += (
                f'<li>'
                f'<a class="booking-entry" href="bookings/{booking.id}" '
                f'style="{entry_style}">'
                f' {booking.booking_name} ({booking.hour_start} -> {booking.hour_end}){rep}'
                f'</a></li>'
            )
        if day != 0:
            date_link = (
                f"<a href='bookings/day/"
                f"{self.year:04d}-{self.month:02d}-{day:02d}'>"
                f"<span class='date'>{day}</span></a>"
            )
            return f"<td>{date_link}<ul> {d} </ul></td>"
        return '<td></td>'

    # formats a week as a tr
    def formatweek(self, theweek, bookings):
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, bookings)
        return f'<tr> {week} </tr>'

    # formats a month as a table
    # filter bookings by year and month
    def formatmonth(self, withyear=True):
        bookings = Booking.objects.filter(date__year=self.year, date__month=self.month)

        cal = '<table border="0" cellpadding="0" cellspacing="0" class="calendar bookings">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'{self.formatweekheader()}\n'
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f'{self.formatweek(week, bookings)}\n'
        cal += '</table>'
        return cal