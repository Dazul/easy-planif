from django.urls import path
from . import views

app_name = 'hr'
urlpatterns = [
    path('hr/', views.HRView.as_view(), name='hr_view'),
    path(
        'hr/employees/',
        views.EmployeeListView.as_view(),
        name='employee_list',
    ),
    path(
        'hr/time-entries/',
        views.WorkCalendarView.as_view(),
        name='work_calendar',
    ),
    path(
        'hr/time-entries/<slug:work_date>/',
        views.WorkDayView.as_view(),
        name='work_day',
    ),
    path(
        'hr/my-time-entries/',
        views.EmployeeWorkCalendarView.as_view(),
        name='employee_work_calendar',
    ),
    path(
        'hr/my-time-entries/<slug:work_date>/',
        views.EmployeeWorkDayView.as_view(),
        name='employee_work_day',
    ),
    path(
        'hr/payroll/',
        views.PayrollSummaryView.as_view(),
        name='payroll_summary',
    ),
]