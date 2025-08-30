from django.test import TestCase
from accounts.models import CustomUser
from django.db import IntegrityError

from .models import Tasks, Authorizations

class TasksTest(TestCase):
    def setUp(self):
        Tasks.objects.create(task_name="T1")
        Tasks.objects.create(task_name="T2")

    def test_tasks(self):
        t1 = Tasks.objects.get(task_name="T1")
        t2 = Tasks.objects.get(task_name="T2")
        self.assertEqual(t1.task_name, "T1")
        self.assertEqual(t2.task_name, "T2")

class AuthorizationsTest(TestCase):
    def setUp(self):
        CustomUser.objects.create_superuser(username='u1', email='', password='')
        Tasks.objects.create(task_name="T1")
        u1 = CustomUser.objects.get(username='u1')
        t1 = Tasks.objects.get(task_name="T1")
        Authorizations.objects.create(user=u1, task=t1)

    def test_authorization(self):
        u1 = CustomUser.objects.get(username='u1')
        t1 = Tasks.objects.get(task_name="T1")
        with self.assertRaises(Exception) as context:
            Authorizations.objects.create(user=u1, task=t1)
        self.assertTrue(isinstance(context.exception, IntegrityError))