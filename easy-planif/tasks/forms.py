from django.forms import ModelForm
from .models import Tasks, Authorizations

class AddTaskForm(ModelForm):
    class Meta:
        model = Tasks
        fields = '__all__'

class AddAuthorizationForm(ModelForm):
    class Meta:
        model = Authorizations
        fields = '__all__'
