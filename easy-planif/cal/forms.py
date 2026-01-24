from django.forms import ModelForm, DateInput

from .models import Event, BookingType

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

class AddBookingTypeForm(ModelForm):
    class Meta:
        model = BookingType
        fields = '__all__'