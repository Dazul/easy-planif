from django.db import models
from accounts.models import CustomUser

class Tasks(models.Model):
    task_name = models.CharField(max_length=50)

class Authorizations(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task = models.ForeignKey(Tasks, on_delete=models.CASCADE)
