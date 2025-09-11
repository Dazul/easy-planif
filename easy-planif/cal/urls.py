from django.urls import path
from . import views

app_name = 'cal'
urlpatterns = [
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/event/new/', views.create_event, name='event_new'),
    path('global_calendar', views.GlobalCalendarView.as_view(), name='global_calendar'),
]