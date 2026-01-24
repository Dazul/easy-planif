from django.forms import ModelForm, DateInput
from django import forms
from .models import Event, BookingType, Booking


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

class AddBookingForm(ModelForm):
    class Meta:
        model = Booking
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'date_report': forms.DateInput(attrs={'type': 'date'}),
            'hour_start': forms.TimeInput(attrs={'type':'time','step':60}),
            'hour_end': forms.TimeInput(attrs={'type':'time','step':60})
        }
        exclude = ['last_author']