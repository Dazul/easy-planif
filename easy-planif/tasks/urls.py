from django.urls import path
from . import views

app_name = 'tasks'
urlpatterns = [
    path('tasks', views.TasksView.as_view(), name='tasks'),
    path('addTask', views.add_task, name='add_task'),
    path('authorizations', views.AuthorizationsView.as_view(), name='authorizations'),
    path('addAuthorization', views.add_authorization, name='addAuthorization'),
    path('commentTypes', views.CommentTypeView.as_view(), name='commentTypes'),
    path('addCommentType', views.add_comment_type, name='addCommentType'),
]
