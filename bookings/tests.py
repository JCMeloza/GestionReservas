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
        booking.full_clean()

    def test_clean_monthly_valid(self):
        booking = self.make_booking(
            frequency="monthly",
            day_of_week=None,
            day_of_month=self.start_date.day,
        )
        booking.full_clean()

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

    def test_check_constraint_rejects_monthly_day_of_month_out_of_range(self):
        # The DB constraint must close the bypass around the field validators
        # (objects.create skips clean()).
        with self.assertRaises(IntegrityError):
            RecurringBooking.objects.create(
                resource=self.resource,
                user=self.user,
                frequency="monthly",
                day_of_week=None,
                day_of_month=32,
                start_time=time(10, 0),
                end_time=time(11, 0),
                start_date=self.start_date,
                end_date=self.start_date + timedelta(days=90),
            )

    def test_clean_unknown_frequency_rejected(self):
        # full_clean() already rejects unknown choices via field validation;
        # this exercises the clean() guard directly (defense in depth).
        booking = self.make_booking(frequency="unknown")
        with self.assertRaises(ValidationError) as ctx:
            booking.clean()
        self.assertIn("Frecuencia de repetición no válida.", str(ctx.exception))

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
        monthly.full_clean()
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
                booking.full_clean()


class RecurringBookingMigrationTests(TransactionTestCase):
    """Regression: the 0006 guard must backfill legacy monthly rows without
    breaking the new CheckConstraint (old schema forced day_of_week NOT NULL),
    and its reverse must restore day_of_week so the AlterField back to NOT
    NULL cannot fail on NULL rows.

    Also covers the reviewer findings on the migration:
    - forward dedupes legacy monthly duplicates that collapse into the same
      slot under the new unique_monthly_recurring (WARNING #1);
    - reverse survives slots where several monthly rows hold different
      day_of_month values and would collide under the restored 0005 unique
      (WARNING #2)."""

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

    def test_0006_forward_dedupes_legacy_monthly_duplicates(self):
        # Under 0005 the unique included day_of_week, so two monthly rows in
        # the same slot (same resource/user/start_time/end_time/start_date/
        # end_date) with different day_of_week values are legal. The backfill
        # normalizes both to day_of_month=start_date.day / day_of_week=None,
        # which would collide under the new unique_monthly_recurring unless
        # the duplicates are removed. Regression for the reviewer's WARNING #1.
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps

        User = old_apps.get_model("users", "User")
        Resource = old_apps.get_model("bookings", "Resource")
        RecurringBooking = old_apps.get_model("bookings", "RecurringBooking")

        resource = Resource.objects.create(name="Pista Duplicada")
        user = User.objects.create_user(username="dup_user", password="pass123")
        start_date = date(2026, 8, 15)
        slot = dict(
            resource=resource,
            user=user,
            frequency="monthly",
            start_time=time(10, 0),
            end_time=time(11, 0),
            start_date=start_date,
            end_date=date(2026, 12, 15),
        )
        first = RecurringBooking.objects.create(day_of_week=0, **slot)
        duplicate = RecurringBooking.objects.create(day_of_week=1, **slot)
        self.assertNotEqual(first.pk, duplicate.pk)

        # Forward: 0006 must apply cleanly and keep exactly one row per slot.
        self.executor.loader.build_graph()
        self.executor.migrate([self.migrate_to])
        new_apps = self.executor.loader.project_state([self.migrate_to]).apps
        NewRecurringBooking = new_apps.get_model("bookings", "RecurringBooking")
        survivors = list(NewRecurringBooking.objects.filter(frequency="monthly"))
        self.assertEqual(len(survivors), 1)
        survivor = survivors[0]
        # The lowest-id row wins, and the normalized row satisfies the monthly
        # branch of the new CheckConstraint (day_of_week IS NULL).
        self.assertEqual(survivor.pk, first.pk)
        self.assertIsNone(survivor.day_of_week)
        self.assertEqual(survivor.day_of_month, start_date.day)

    def test_0006_reverse_handles_colliding_monthly_rows(self):
        # Under 0006 two monthly rows in the same slot with different
        # day_of_month are legal at DB level: the CheckConstraint checks the
        # range (1-31) and day_of_week IS NULL, not start_date.day ==
        # day_of_month — that coherence is clean()-only and skippable via
        # objects.create. The reverse restores day_of_week=start_date.weekday()
        # for both, which would collide under the restored 0005 unique
        # (which includes day_of_week). Regression for the reviewer's
        # WARNING #2: the reverse must complete and keep one row per slot.
        self.executor.migrate([self.migrate_to])
        new_apps = self.executor.loader.project_state([self.migrate_to]).apps

        User = new_apps.get_model("users", "User")
        Resource = new_apps.get_model("bookings", "Resource")
        RecurringBooking = new_apps.get_model("bookings", "RecurringBooking")

        resource = Resource.objects.create(name="Pista Colisión")
        user = User.objects.create_user(username="collision_user", password="pass123")
        start_date = date(2026, 8, 15)  # day 15 → weekday() == 5
        slot = dict(
            resource=resource,
            user=user,
            frequency="monthly",
            day_of_week=None,
            start_time=time(10, 0),
            end_time=time(11, 0),
            start_date=start_date,
            end_date=date(2026, 12, 15),
        )
        # Created first (lowest id) but incoherent: day_of_month does not match
        # start_date.day. The coherent row must survive the reverse even
        # though it has the higher id.
        incoherent = RecurringBooking.objects.create(day_of_month=20, **slot)
        coherent = RecurringBooking.objects.create(
            day_of_month=start_date.day, **slot
        )
        self.assertLess(incoherent.pk, coherent.pk)

        # Reverse: must complete without crashing and keep the coherent row
        # with its weekday restored.
        self.executor.loader.build_graph()
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps
        OldRecurringBooking = old_apps.get_model("bookings", "RecurringBooking")
        rows = list(OldRecurringBooking.objects.filter(frequency="monthly"))
        self.assertEqual(len(rows), 1)
        survivor = rows[0]
        self.assertEqual(survivor.pk, coherent.pk)
        self.assertEqual(survivor.day_of_week, start_date.weekday())
