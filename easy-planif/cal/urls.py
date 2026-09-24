from django.urls import path
from . import views

app_name = 'cal'
urlpatterns = [
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/event/new/', views.create_event, name='event_new'),
    path('global_calendar', views.GlobalCalendarView.as_view(), name='global_calendar'),
    path('replacements', views.ReplacementCalendarView.as_view(), name='replacements'),
    path('replacements/replace', views.replace, name='replace'),
    path('planning', views.PlanningView.as_view(), name='planning'),
    path('planning/event/update', views.update_event, name='planning_event_update'),
    path('calendar/toggle_replacement', views.toggle_replacement, name='toggle_replacement'),
]