from accounts.models import CustomUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from tasks.models import Tasks, Authorizations

class Event(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    tasks = models.ForeignKey(Tasks, on_delete=models.CASCADE, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_if_needed = models.BooleanField(default=False)
    date = models.DateTimeField()
    is_replaceable = models.BooleanField(default=False)

    class Meta:
        permissions = [
            ('assign_task', 'Assign a Task'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_event_per_day_for_user",
            )
        ]

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
        if self.is_if_needed and not self.is_available:
            raise ValidationError(
                {"content": "Event cannot be if needed and not available"}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class ReplacementRequest(models.Model):
    """A user offering to take another user's replaceable event.

    Created when an authorized user clicks a replaceable event; it
    takes effect only once an HR staff member validates it.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VALIDATED = "validated", "Validated"
        REFUSED = "refused", "Refused"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="replacement_requests",
    )
    replacement_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="replacement_requests",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_replacement_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # one live request per event: a refused request stays for the
        # record, so uniqueness only covers the pending one
        constraints = [
            models.UniqueConstraint(
                fields=["event"],
                condition=models.Q(status="pending"),
                name="unique_pending_replacement_request_per_event",
            )
        ]

    def __str__(self):
        return (
            f"{self.replacement_user} replaces {self.event.user} "
            f"on {self.event.date} ({self.status})"
        )

    def validate_replacement(self, reviewed_by):
        """Apply the replacement to the event. Must be called on a
        pending request only."""
        if self.status != self.Status.PENDING:
            raise ValidationError("Only pending requests can be validated.")
        if not Authorizations.objects.filter(
            user=self.replacement_user, task=self.event.tasks
        ).exists():
            raise ValidationError(
                "The replacement user is not authorized for the task."
            )
        event = self.event
        event.user = self.replacement_user
        event.is_replaceable = False
        event.save()  # re-runs full_clean(), re-checking authorizations
        self.status = self.Status.VALIDATED
        self.reviewed_by = reviewed_by
        self.save()

    def refuse_replacement(self, reviewed_by):
        """Refuse the request; the slot becomes takeable again."""
        if self.status != self.Status.PENDING:
            raise ValidationError("Only pending requests can be refused.")
        self.status = self.Status.REFUSED
        self.reviewed_by = reviewed_by
        self.save()

class BookingType(models.Model):
    booking_type = models.CharField(max_length=100)
    color = models.CharField(
        max_length=7,
        default="#17a2b8",
        help_text="Color code shown in the bookings calendar (hex, e.g. #17a2b8)",
    )

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

    class Meta:
        permissions = [
            ('bookings_view', 'View bookings'),
            ('bookings_manager', 'Manage bookings'),
        ]

    def clean(self):
        super().clean()
        if self.hour_end < self.hour_start:
            raise ValidationError({"hour_start": "Booking start must be before booking end"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)