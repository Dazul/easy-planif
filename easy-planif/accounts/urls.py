from django.urls import path
from django.views.generic.base import TemplateView
from . import views

urlpatterns = [
    path('users/', views.UsersView.as_view(), name="users"),
]
