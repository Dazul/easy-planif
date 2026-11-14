from django.forms import ModelForm, DateInput
from django import forms
from .models import Event


class EventForm(ModelForm):
  class Meta:
    model = Event
    widgets = {
      'date': DateInput(format='%d-%m-%Y'),
    }
    fields = ['is_available', 'is_if_needed', 'date']

  def __init__(self, *args, **kwargs):
    super(EventForm, self).__init__(*args, **kwargs)
    self.fields['date'].input_formats = ('%d-%m-%Y',)