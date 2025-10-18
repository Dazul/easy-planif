from accounts.models import CustomUser
from django.db import models
from tasks.models import Tasks

class Event(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    tasks = models.ForeignKey(Tasks, on_delete=models.CASCADE, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    date = models.DateTimeField()
