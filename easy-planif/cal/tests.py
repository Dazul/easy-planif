from django.core.exceptions import ValidationError
from django.test import TestCase
from accounts.models import CustomUser
from datetime import datetime, timezone, date, time

from tasks.models import Tasks, Authorizations
from .models import Event, Booking


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

class CreateBookingTest(TestCase):
     def test_booking_creation(self):
         _ = Booking.objects.create(
         booking_name="b1",
         date = date(2019, 10, 5),
         hour_start = time(hour=10, minute=0, second=0),
         hour_end = time(hour=20, minute=0, second=0),
         group_leader_name = "Boby",
         group_leader_address = "home",
         group_leader_email = "boby@home.com",
         nbr_adult = 10,
         nbr_child = 10,
         nbr_wheelchair = 0,
         price_adult = 10,
         price_child = 10,
         meal_included = False,
         meal_price_adult = 12,
         meal_price_child = 6,
         price_total = 100,
         )

class CreateBadTimeBookingTest(TestCase):
     def test_booking_creation(self):
        with self.assertRaises(Exception) as context:
            _ = Booking.objects.create(
                booking_name="b1",
                date=date(2019, 10, 5),
                hour_start=time(hour=20, minute=0, second=0),
                hour_end=time(hour=10, minute=0, second=0),
                group_leader_name="Boby",
                group_leader_address="home",
                group_leader_email="boby@home.com",
                nbr_adult=10,
                nbr_child=10,
                nbr_wheelchair=0,
                price_adult=10,
                price_child=10,
                meal_included=False,
                meal_price_adult=12,
                meal_price_child=6,
                price_total=100,
            )
        self.assertTrue(isinstance(context.exception, ValidationError))


class CreateNegativePriceAdultBookingTest(TestCase):
    def test_booking_creation(self):
        with self.assertRaises(Exception) as context:
            _ = Booking.objects.create(
                booking_name="b1",
                date=date(2019, 10, 5),
                hour_start=time(hour=10, minute=0, second=0),
                hour_end=time(hour=20, minute=0, second=0),
                group_leader_name="Boby",
                group_leader_address="home",
                group_leader_email="boby@home.com",
                nbr_adult=10,
                nbr_child=10,
                nbr_wheelchair=0,
                price_adult=-10,
                price_child=10,
                meal_included=False,
                meal_price_adult=12,
                meal_price_child=6,
                price_total=100,
            )
        self.assertTrue(isinstance(context.exception, ValidationError))


class CreateNegativePriceKidBookingTest(TestCase):
    def test_booking_creation(self):
        with self.assertRaises(Exception) as context:
            _ = Booking.objects.create(
                booking_name="b1",
                date=date(2019, 10, 5),
                hour_start=time(hour=10, minute=0, second=0),
                hour_end=time(hour=20, minute=0, second=0),
                group_leader_name="Boby",
                group_leader_address="home",
                group_leader_email="boby@home.com",
                nbr_adult=10,
                nbr_child=10,
                nbr_wheelchair=0,
                price_adult=10,
                price_child=-10,
                meal_included=False,
                meal_price_adult=12,
                meal_price_child=6,
                price_total=100,
            )
        self.assertTrue(isinstance(context.exception, ValidationError))


class CreateNegativePriceMealAdultBookingTest(TestCase):
    def test_booking_creation(self):
        with self.assertRaises(Exception) as context:
            _ = Booking.objects.create(
                booking_name="b1",
                date=date(2019, 10, 5),
                hour_start=time(hour=10, minute=0, second=0),
                hour_end=time(hour=20, minute=0, second=0),
                group_leader_name="Boby",
                group_leader_address="home",
                group_leader_email="boby@home.com",
                nbr_adult=10,
                nbr_child=10,
                nbr_wheelchair=0,
                price_adult=10,
                price_child=10,
                meal_included=False,
                meal_price_adult=-12,
                meal_price_child=6,
                price_total=100,
            )
        self.assertTrue(isinstance(context.exception, ValidationError))


class CreateNegativePriceMealKidBookingTest(TestCase):
    def test_booking_creation(self):
        with self.assertRaises(Exception) as context:
            _ = Booking.objects.create(
                booking_name="b1",
                date=date(2019, 10, 5),
                hour_start=time(hour=10, minute=0, second=0),
                hour_end=time(hour=20, minute=0, second=0),
                group_leader_name="Boby",
                group_leader_address="home",
                group_leader_email="boby@home.com",
                nbr_adult=10,
                nbr_child=10,
                nbr_wheelchair=0,
                price_adult=10,
                price_child=10,
                meal_included=False,
                meal_price_adult=12,
                meal_price_child=-6,
                price_total=100,
            )
        self.assertTrue(isinstance(context.exception, ValidationError))