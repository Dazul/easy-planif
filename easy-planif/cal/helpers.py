import calendar
from datetime import datetime, timedelta, date

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