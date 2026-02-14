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
        permissions = [
            ('Trainer', 'Trainer rights'),
        ]

class CommentType(models.Model):
    comment_type = models.CharField(max_length=50)

    def __str__(self):
        return self.comment_type

class Comment(models.Model):
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="comment_employee")
    comment = models.TextField()
    type = models.ForeignKey(CommentType, on_delete=models.CASCADE)
    instructor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="comment_instructor")
    date = models.DateField(auto_now_add=True)

    class Meta:
        permissions = [
            ('Trainer', 'Trainer rights'),
        ]