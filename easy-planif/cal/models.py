from accounts.models import CustomUser
from django.core.exceptions import ValidationError
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