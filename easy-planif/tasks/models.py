from django.db import models
from accounts.models import CustomUser

class Tasks(models.Model):
    task_name = models.CharField(max_length=50)

    def __str__(self):
        return self.task_name

class Authorizations(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task = models.ForeignKey(Tasks, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('user', 'task'))
