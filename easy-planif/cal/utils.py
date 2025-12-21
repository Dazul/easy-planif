from calendar import HTMLCalendar

from tasks.models import Tasks, Authorizations
from accounts.models import CustomUser
from .models import Event
from django.template.loader import render_to_string

class Calendar(HTMLCalendar):
    def __init__(self, current_user=None, year=None, month=None):
        self.year = year
        self.month = month
        self.current_user = current_user
        super(Calendar, self).__init__()

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
                    d += '<li>Available</li>'
                else:
                    d += f'<li> {event.tasks} </li>'
        if not event_found:
            d += f'<div class="box" onclick="createAvailableEvent(\'{day}-{self.month}-{self.year}\')"></div>'

        if day != 0:
            return f"<td><span class='date'>{day}</span><ul> {d} </ul></td>"
        return '<td></td>'

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
        super(Calendar, self).__init__()

    def formatday(self, day, events, user_id):
        events_per_day = events.filter(date__day=day, user__id=user_id)
        d = ''
        if len(events_per_day) != 0:
            for event in events_per_day:
                if event.is_available:
                    d += '<li>Available</li>'
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

class PlanningCalendar(GlobalCalendar):
    def __init__(self):
        super(GlobalCalendar, self).__init__()

    def define_form(self, event_id, request):
        tasks = []
        user = CustomUser.objects.get(id=Event.objects.get(id=event_id).user_id)
        auths = Authorizations.objects.all().filter(user=user)
        if 'task' in request.GET:
            found = False
            for auth in auths:
                if str(auth.task_id) == request.GET['task']:
                    tasks.append(Tasks.objects.get(id=auth.task_id))
                    found = True
                    break
            if not found:
                return '---'
        else:
            for auth in auths:
                tasks.append(Tasks.objects.get(id=auth.task_id))
        week_date = None
        task = None
        if 'week_date' in request.GET.keys():
            week_date = request.GET['week_date']
        if 'task' in request.GET.keys():
            task = request.GET['task']
        return render_to_string("cal/dropdown_planning.html", {'event_id': event_id, 'tasks': tasks, 'week_date': week_date, 'task': task}, request=request)

    def formatday(self, day, events, user_id, request):
        events_per_day = events.filter(date__day=day, user__id=user_id)
        d = ''
        if len(events_per_day) != 0:
            for event in events_per_day:
                if event.is_available:
                    d += self.define_form(event.id, request)
                else:
                    d += f'<li> {event.tasks} </li>'
        return f'<td style="height:30px;"><ul> {d} </ul></td>'

    def formatweek(self, theweek, request):
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
                week += self.formatday(d.day, events, uid, request)
            week += '</tr>'
        return week