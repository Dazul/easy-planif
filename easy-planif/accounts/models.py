from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class CustomUser(AbstractUser):
    username = models.CharField(max_length=40, unique=True)
    email = models.CharField(max_length=200)

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    # add additional fields in here

    def __str__(self):
        return self.username
