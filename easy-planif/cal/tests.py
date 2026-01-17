from django.core.exceptions import ValidationError
from django.test import TestCase
from accounts.models import CustomUser
from datetime import datetime, timezone

from tasks.models import Tasks, Authorizations
from .models import Event

class EventCreateTest(TestCase):
    def setUp(self):
        CustomUser.objects.create_superuser(username='u3', email='', password='')

    def test_event_creation(self):
        user = CustomUser.objects.get(username='u3')
        d = datetime(2019, 10, 5, tzinfo=timezone.utc)
        Event.objects.create(user=user, date=d)
        ev1 = Event.objects.get(user=user, date=d)
        self.assertEqual(ev1.user.username, 'u3')
        self.assertEqual(ev1.is_available, True)

class EventModifyTest(TestCase):
    def setUp(self):
        CustomUser.objects.create_superuser(username='u1', email='', password='')
        Tasks.objects.create(task_name="T1")
        u1 = CustomUser.objects.get(username='u1')
        t1 = Tasks.objects.get(task_name="T1")
        Authorizations.objects.create(user=u1, task=t1)

    def test_event_modify(self):
        user = CustomUser.objects.get(username='u1')
        d = datetime(2019, 10, 5, tzinfo=timezone.utc)
        Event.objects.create(user=user, date=d)
        ev1 = Event.objects.get(user=user, date=d)
        self.assertEqual(ev1.user.username, 'u1')
        self.assertEqual(ev1.is_available, True)
        task = Tasks.objects.get(task_name="T1")
        ev1.tasks = task
        ev1.is_available = False
        ev1.save()
        ev2 = Event.objects.get(user=user, date=d)
        self.assertEqual(ev1.user.username, 'u1')
        self.assertEqual(ev1.is_available, False)
        self.assertEqual(ev2.tasks.task_name, 'T1')

class EventBadModifyTest(TestCase):
    def setUp(self):
        CustomUser.objects.create_superuser(username='u2', email='', password='')
        Tasks.objects.create(task_name="T2")
        u2 = CustomUser.objects.get(username='u2')
        t2 = Tasks.objects.get(task_name="T2")
        Authorizations.objects.create(user=u2, task=t2)

    def test_event_bad_modify(self):
        user = CustomUser.objects.get(username='u2')
        d = datetime(2019, 10, 5, tzinfo=timezone.utc)
        Event.objects.create(user=user, date=d)
        ev1 = Event.objects.get(user=user, date=d)
        self.assertEqual(ev1.user.username, 'u2')
        self.assertEqual(ev1.is_available, True)
        task = Tasks.objects.get(task_name="T2")
        ev1.tasks = task
        with self.assertRaises(Exception) as context:
            ev1.save()
        self.assertTrue(isinstance(context.exception, ValidationError))

class EventFreeAvailableTest(TestCase):
    def setUp(self):
        CustomUser.objects.create_superuser(username='u1', email='', password='')
    def test_event_free_available(self):
        user = CustomUser.objects.get(username='u1')
        d = datetime(2019, 10, 5, tzinfo=timezone.utc)
        Event.objects.create(user=user, date=d)
        ev1 = Event.objects.get(user=user, date=d)
        self.assertEqual(ev1.user.username, 'u1')
        self.assertEqual(ev1.is_available, True)
        ev1.is_available = False
        with self.assertRaises(Exception) as context:
            ev1.save()
        self.assertTrue(isinstance(context.exception, ValidationError))

class EventUnauthorizedTest(TestCase):
    def setUp(self):
        CustomUser.objects.create_superuser(username='u1', email='', password='')
        CustomUser.objects.create_superuser(username='u2', email='', password='')
        Tasks.objects.create(task_name="T1")
        Tasks.objects.create(task_name="T2")
        u1 = CustomUser.objects.get(username='u1')
        t1 = Tasks.objects.get(task_name="T1")
        Authorizations.objects.create(user=u1, task=t1)
        u2 = CustomUser.objects.get(username='u2')
        t2 = Tasks.objects.get(task_name="T2")
        Authorizations.objects.create(user=u2, task=t2)

    def test_event_unauthorized(self):
        user = CustomUser.objects.get(username='u2')
        d = datetime(2019, 10, 5, tzinfo=timezone.utc)
        Event.objects.create(user=user, date=d)
        ev1 = Event.objects.get(user=user, date=d)
        self.assertEqual(ev1.user.username, 'u2')
        self.assertEqual(ev1.is_available, True)
        task = Tasks.objects.get(task_name="T1")
        ev1.tasks = task
        ev1.is_available = False
        with self.assertRaises(Exception) as context:
            ev1.save()
        self.assertTrue(isinstance(context.exception, ValidationError))