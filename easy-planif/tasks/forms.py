from django.forms import ModelForm
from .models import Tasks, Authorizations, CommentType, Comment

class AddTaskForm(ModelForm):
    class Meta:
        model = Tasks
        fields = '__all__'

class AddAuthorizationForm(ModelForm):
    class Meta:
        model = Authorizations
        fields = '__all__'

class AddCommentTypeForm(ModelForm):
    class Meta:
        model = CommentType
        fields = '__all__'

class AddCommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['employee', 'comment', 'type']