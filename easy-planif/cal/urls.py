from django.urls import path
from . import views

app_name = 'cal'
urlpatterns = [
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/event/new/', views.create_event, name='event_new'),
    path('global_calendar', views.GlobalCalendarView.as_view(), name='global_calendar'),
    path('planning', views.PlanningView.as_view(), name='planning'),
    path('planning/event/update', views.update_event, name='planning_event_update'),
    path('bookingTypes', views.BookingTypeView.as_view(), name='booking_type'),
    path('addBookingType', views.add_booking_type, name='booking_type'),
]