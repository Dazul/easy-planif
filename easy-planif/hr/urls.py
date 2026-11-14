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
]