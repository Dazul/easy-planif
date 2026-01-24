from accounts.models import CustomUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from tasks.models import Tasks, Authorizations

class Event(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    tasks = models.ForeignKey(Tasks, on_delete=models.CASCADE, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    date = models.DateTimeField()

    def clean(self):
        super().clean()

        if self.tasks is not None and self.is_available:
            raise ValidationError({"content": "Event cannot have a task and be available"})

        if not self.is_available:
            if self.tasks is None:
                raise ValidationError({"content": "Event must have a task is not available"})
            auth = Authorizations.objects.filter(user=self.user, task=self.tasks)
            if len(auth) == 0:
                raise ValidationError({"content": "Unauthorized"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class BookingType(models.Model):
    booking_type = models.CharField(max_length=100)

    def __str__(self):
        return self.booking_type

class Booking(models.Model):
    booking_name = models.CharField(max_length=100)
    booking_type = models.ForeignKey(BookingType, on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateField()
    date_report = models.DateField(blank=True, null=True)
    come_all_weather = models.BooleanField(default=False)
    hour_start = models.TimeField()
    hour_end = models.TimeField()
    group_leader_name = models.CharField(max_length=100)
    group_leader_address = models.TextField()
    group_leader_email = models.EmailField()
    group_leader_phone = models.CharField(max_length=100, blank=True, null=True)
    nbr_adult = models.PositiveIntegerField()
    nbr_child = models.PositiveIntegerField()
    nbr_wheelchair = models.PositiveIntegerField(blank=True, null=True)
    price_adult = models.FloatField(validators=[MinValueValidator(0)], default=0)
    price_child = models.FloatField(validators=[MinValueValidator(0)], default=0)
    meal_included = models.BooleanField(default=False)
    meal_price_adult = models.FloatField(validators=[MinValueValidator(0)], default=0)
    meal_price_child = models.FloatField(validators=[MinValueValidator(0)], default=0)
    price_total = models.FloatField()
    comments = models.TextField(blank=True, null=True)
    meal_comments = models.TextField(blank=True, null=True)
    last_author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)

    def clean(self):
        super().clean()
        if self.hour_end < self.hour_start:
            raise ValidationError({"hour_start": "Booking start must be before booking end"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)