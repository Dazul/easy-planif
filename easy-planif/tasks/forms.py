from django.forms import ModelForm
from .models import Tasks, Authorizations, CommentType

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