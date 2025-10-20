from django.forms import ModelForm, DateInput

from cal.models import Event

class EventForm(ModelForm):
  class Meta:
    model = Event
    widgets = {
      'date': DateInput(format='%d-%m-%Y'),
    }
    fields = ['is_available', 'date']

  def __init__(self, *args, **kwargs):
    super(EventForm, self).__init__(*args, **kwargs)
    self.fields['date'].input_formats = ('%d-%m-%Y',)