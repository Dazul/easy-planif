from django.urls import path
from . import views

app_name = 'hr'
urlpatterns = [
    path('hr/', views.HRView.as_view(), name='hr_view'),
]