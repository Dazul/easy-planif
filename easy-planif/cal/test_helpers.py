from datetime import date, datetime

from django.test import SimpleTestCase

from .helpers import (
    get_date,
    get_date_week,
    next_month,
    next_week,
    prev_month,
    prev_week,
)


class HelpersTest(SimpleTestCase):
    def test_get_date_with_none_returns_today(self):
        result = get_date(None)
        self.assertEqual(
            (result.year, result.month, result.day),
            (datetime.today().year, datetime.today().month, datetime.today().day),
        )

    def test_get_date_parses_year_month(self):
        result = get_date("2019-10")
        self.assertEqual(result, date(2019, 10, 1))

    def test_get_date_rejects_full_date(self):
        # get_date expects "YYYY-MM" only; a day component crashes.
        # The view only feeds it query params like "2019-10".
        with self.assertRaises(ValueError):
            get_date("2019-10-25")

    def test_get_date_week_with_none_returns_today(self):
        result = get_date_week(None)
        self.assertEqual(
            (result.year, result.month, result.day),
            (datetime.today().year, datetime.today().month, datetime.today().day),
        )

    def test_get_date_week_parses_full_date(self):
        result = get_date_week("2019-10-25")
        self.assertEqual(result, date(2019, 10, 25))

    def test_prev_month_from_mid_month(self):
        # Day is normalized to the first of the month before stepping back
        self.assertEqual(prev_month(date(2019, 10, 15)), "month=2019-9")

    def test_prev_month_year_rollover(self):
        self.assertEqual(prev_month(date(2020, 1, 1)), "month=2019-12")

    def test_next_month_from_mid_month(self):
        self.assertEqual(next_month(date(2019, 10, 15)), "month=2019-11")

    def test_next_month_year_rollover(self):
        self.assertEqual(next_month(date(2019, 12, 3)), "month=2020-1")

    def test_next_month_february_leap_year(self):
        # Feb 2020 has 29 days: stepping from Feb 20 lands on Mar 1
        self.assertEqual(next_month(date(2020, 2, 20)), "month=2020-3")

    def test_prev_week(self):
        self.assertEqual(prev_week(date(2019, 10, 15)), "week_date=2019-10-8")

    def test_next_week(self):
        self.assertEqual(next_week(date(2019, 10, 15)), "week_date=2019-10-22")

    def test_prev_week_month_and_year_rollover(self):
        self.assertEqual(prev_week(date(2020, 1, 3)), "week_date=2019-12-27")

    def test_next_week_month_rollover(self):
        self.assertEqual(next_week(date(2019, 10, 29)), "week_date=2019-11-5")
