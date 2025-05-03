from django.urls import path
from . import views

app_name = 'tasks'
urlpatterns = [
    path('tasks', views.TasksView.as_view(), name='tasks'),
    path('addTask', views.add_task, name='add_task'),
]
