from django.forms import ModelForm, DateInput
from django import forms
from .models import Event, BookingType, Booking


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
class AddBookingTypeForm(ModelForm):
    class Meta:
        model = BookingType
        fields = '__all__'
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }

class AddBookingForm(ModelForm):
    class Meta:
        model = Booking
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'date_report': forms.DateInput(attrs={'type': 'date'}),
            'hour_start': forms.TimeInput(attrs={'type':'time','step':60}),
            'hour_end': forms.TimeInput(attrs={'type':'time','step':60}),
            # hooks for the client-side price autocomputation
            'nbr_adult': forms.NumberInput(attrs={'data-price-part': 'adult'}),
            'nbr_child': forms.NumberInput(attrs={'data-price-part': 'child'}),
            'price_adult': forms.NumberInput(attrs={'data-price-part': 'price_adult'}),
            'price_child': forms.NumberInput(attrs={'data-price-part': 'price_child'}),
            'meal_included': forms.CheckboxInput(attrs={'data-price-part': 'meal_included'}),
            'meal_price_adult': forms.NumberInput(attrs={'data-price-part': 'meal_price_adult'}),
            'meal_price_child': forms.NumberInput(attrs={'data-price-part': 'meal_price_child'}),
            'price_total': forms.NumberInput(attrs={'data-price-total': 'true'}),
        }
        exclude = ['last_author']

    def clean(self):
        cleaned_data = super().clean()
        # server-side check of the autocomputed total (the client can
        # also fill it, but we never trust it)
        nbr_adult = cleaned_data.get('nbr_adult') or 0
        nbr_child = cleaned_data.get('nbr_child') or 0
        price_adult = cleaned_data.get('price_adult') or 0
        price_child = cleaned_data.get('price_child') or 0
        meal_included = cleaned_data.get('meal_included')
        meal_price_adult = cleaned_data.get('meal_price_adult') or 0
        meal_price_child = cleaned_data.get('meal_price_child') or 0
        price_total = cleaned_data.get('price_total') or 0

        expected = nbr_adult * price_adult + nbr_child * price_child
        if meal_included:
            expected += nbr_adult * meal_price_adult + nbr_child * meal_price_child
        if cleaned_data.get('price_total') is not None and price_total != expected:
            self.add_error(
                'price_total',
                f"Total price must be {expected} "
                f"({nbr_adult}x{price_adult} + {nbr_child}x{price_child}"
                + (f" + meals" if meal_included else "") + ").",
            )
        return cleaned_data
