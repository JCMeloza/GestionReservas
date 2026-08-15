from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from bookings.models import RecurringBooking, Resource
from users.models import User


class RecurringBookingModelTests(TestCase):

    def setUp(self):
        self.resource = Resource.objects.create(name="Pista Central")
        self.user = User.objects.create_user(
            username="recurring_user",
            password="pass123",
        )
        self.start_date = date(2026, 8, 17)
        self.start_weekday = self.start_date.weekday()

    def make_booking(self, **kwargs):
        defaults = {
            "resource": self.resource,
            "user": self.user,
            "frequency": "weekly",
            "day_of_week": self.start_weekday,
            "day_of_month": None,
            "start_time": time(10, 0),
            "end_time": time(11, 0),
            "start_date": self.start_date,
            "end_date": self.start_date + timedelta(days=30),
        }
        defaults.update(kwargs)
        return RecurringBooking(**defaults)

    def assert_clean_error(self, booking, expected_message):
        with self.assertRaises(ValidationError) as ctx:
            booking.full_clean()
        self.assertIn(expected_message, str(ctx.exception))

    def test_clean_weekly_valid(self):
        booking = self.make_booking()
        self.assertIsNone(booking.full_clean())

    def test_clean_monthly_valid(self):
        booking = self.make_booking(
            frequency="monthly",
            day_of_week=None,
            day_of_month=self.start_date.day,
        )
        self.assertIsNone(booking.full_clean())

    def test_clean_weekly_with_day_of_month_rejected(self):
        booking = self.make_booking(day_of_month=15)
        self.assert_clean_error(
            booking,
            "Selecciona un día de la semana (semanal) o un día del mes (mensual).",
        )

    def test_clean_weekly_without_day_of_week_rejected(self):
        booking = self.make_booking(day_of_week=None)
        self.assert_clean_error(
            booking,
            "Selecciona un día de la semana (semanal) o un día del mes (mensual).",
        )

    def test_clean_monthly_with_day_of_week_rejected(self):
        booking = self.make_booking(
            frequency="monthly",
            day_of_week=self.start_weekday,
            day_of_month=self.start_date.day,
        )
        self.assert_clean_error(
            booking,
            "Selecciona un día de la semana (semanal) o un día del mes (mensual).",
        )

    def test_clean_monthly_without_day_of_month_rejected(self):
        booking = self.make_booking(
            frequency="monthly",
            day_of_week=None,
            day_of_month=None,
        )
        self.assert_clean_error(
            booking,
            "Selecciona un día de la semana (semanal) o un día del mes (mensual).",
        )

    def test_clean_weekly_day_mismatch_rejected(self):
        booking = self.make_booking(
            day_of_week=(self.start_weekday + 1) % 7,
        )
        self.assert_clean_error(
            booking,
            "La fecha inicial no coincide con el día seleccionado.",
        )

    def test_clean_monthly_day_mismatch_rejected(self):
        day_of_month = 1 if self.start_date.day != 1 else 2
        booking = self.make_booking(
            frequency="monthly",
            day_of_week=None,
            day_of_month=day_of_month,
        )
        self.assert_clean_error(
            booking,
            "La fecha inicial no coincide con el día seleccionado.",
        )

    def test_check_constraint_rejects_weekly_with_day_of_month(self):
        with self.assertRaises(IntegrityError):
            RecurringBooking.objects.create(
                resource=self.resource,
                user=self.user,
                frequency="weekly",
                day_of_week=self.start_weekday,
                day_of_month=15,
                start_time=time(10, 0),
                end_time=time(11, 0),
                start_date=self.start_date,
                end_date=self.start_date + timedelta(days=30),
            )

    def test_check_constraint_rejects_monthly_with_day_of_week(self):
        with self.assertRaises(IntegrityError):
            RecurringBooking.objects.create(
                resource=self.resource,
                user=self.user,
                frequency="monthly",
                day_of_week=self.start_weekday,
                day_of_month=self.start_date.day,
                start_time=time(10, 0),
                end_time=time(11, 0),
                start_date=self.start_date,
                end_date=self.start_date + timedelta(days=30),
            )

    def test_unique_weekly_recurring_rejects_duplicate(self):
        RecurringBooking.objects.create(
            resource=self.resource,
            user=self.user,
            frequency="weekly",
            day_of_week=self.start_weekday,
            day_of_month=None,
            start_time=time(10, 0),
            end_time=time(11, 0),
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=30),
        )
        with self.assertRaises(IntegrityError):
            RecurringBooking.objects.create(
                resource=self.resource,
                user=self.user,
                frequency="weekly",
                day_of_week=self.start_weekday,
                day_of_month=None,
                start_time=time(10, 0),
                end_time=time(11, 0),
                start_date=self.start_date,
                end_date=self.start_date + timedelta(days=30),
            )

    def test_unique_monthly_recurring_rejects_duplicate(self):
        RecurringBooking.objects.create(
            resource=self.resource,
            user=self.user,
            frequency="monthly",
            day_of_week=None,
            day_of_month=self.start_date.day,
            start_time=time(10, 0),
            end_time=time(11, 0),
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=90),
        )
        with self.assertRaises(IntegrityError):
            RecurringBooking.objects.create(
                resource=self.resource,
                user=self.user,
                frequency="monthly",
                day_of_week=None,
                day_of_month=self.start_date.day,
                start_time=time(10, 0),
                end_time=time(11, 0),
                start_date=self.start_date,
                end_date=self.start_date + timedelta(days=90),
            )

    def test_weekly_and_monthly_series_can_coexist(self):
        RecurringBooking.objects.create(
            resource=self.resource,
            user=self.user,
            frequency="weekly",
            day_of_week=self.start_weekday,
            day_of_month=None,
            start_time=time(10, 0),
            end_time=time(11, 0),
            start_date=self.start_date,
            end_date=self.start_date + timedelta(days=30),
        )
        monthly = self.make_booking(
            frequency="monthly",
            day_of_week=None,
            day_of_month=self.start_date.day,
        )
        self.assertIsNone(monthly.full_clean())
        monthly.save()
        self.assertEqual(RecurringBooking.objects.count(), 2)

    def test_day_of_month_validator_rejects_out_of_range(self):
        for value in (0, 32):
            with self.subTest(day_of_month=value):
                booking = self.make_booking(
                    frequency="monthly",
                    day_of_week=None,
                    day_of_month=value,
                )
                with self.assertRaises(ValidationError) as ctx:
                    booking.full_clean()
                self.assertIn("day_of_month", ctx.exception.message_dict)

    def test_day_of_month_validator_accepts_boundaries(self):
        for start_date, value in ((date(2026, 8, 1), 1), (date(2026, 8, 31), 31)):
            with self.subTest(day_of_month=value):
                booking = self.make_booking(
                    frequency="monthly",
                    day_of_week=None,
                    day_of_month=value,
                    start_date=start_date,
                )
                self.assertIsNone(booking.full_clean())


class RecurringBookingMigrationTests(TransactionTestCase):
    """Regression: the 0006 guard must backfill legacy monthly rows without
    breaking the new CheckConstraint (old schema forced day_of_week NOT NULL),
    and its reverse must restore day_of_week so the AlterField back to NOT
    NULL cannot fail on NULL rows."""

    migrate_from = ("bookings", "0005_alter_recurringbooking_options_and_more")
    migrate_to = ("bookings", "0006_remove_recurringbooking_unique_recurring_booking_and_more")

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)

    def tearDown(self):
        # Leave the test DB schema at the latest state so later tests are unaffected.
        self.executor.loader.build_graph()
        self.executor.migrate([self.migrate_to])
        super().tearDown()

    def test_0006_backfills_legacy_monthly_rows_and_reverse_restores_day_of_week(self):
        # State at 0005: insert a legacy monthly row (day_of_week NOT NULL,
        # no day_of_month column yet).
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps

        User = old_apps.get_model("users", "User")
        Resource = old_apps.get_model("bookings", "Resource")
        RecurringBooking = old_apps.get_model("bookings", "RecurringBooking")

        resource = Resource.objects.create(name="Pista Legacy")
        user = User.objects.create_user(username="legacy_user", password="pass123")
        start_date = date(2026, 8, 15)
        legacy = RecurringBooking.objects.create(
            resource=resource,
            user=user,
            frequency="monthly",
            day_of_week=0,  # legacy: old schema forced NOT NULL
            start_time=time(10, 0),
            end_time=time(11, 0),
            start_date=start_date,
            end_date=date(2026, 12, 15),
        )

        # Forward: 0006 must apply cleanly and the row must satisfy the monthly
        # branch of the new CheckConstraint (day_of_week IS NULL).
        self.executor.loader.build_graph()
        self.executor.migrate([self.migrate_to])
        new_apps = self.executor.loader.project_state([self.migrate_to]).apps
        NewRecurringBooking = new_apps.get_model("bookings", "RecurringBooking")
        row = NewRecurringBooking.objects.get(pk=legacy.pk)
        self.assertIsNone(row.day_of_week)
        self.assertEqual(row.day_of_month, start_date.day)

        # Reverse: 0005 must restore the weekday so the AlterField back to
        # NOT NULL succeeds with no NULL rows left behind.
        self.executor.loader.build_graph()
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps
        OldRecurringBooking = old_apps.get_model("bookings", "RecurringBooking")
        row = OldRecurringBooking.objects.get(pk=legacy.pk)
        self.assertEqual(row.day_of_week, start_date.weekday())
