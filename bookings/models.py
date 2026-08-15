from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Resource(models.Model):

    name = models.CharField(
        max_length=50,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.name



class Availability(models.Model):

    DAYS_OF_WEEK = [
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]


    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="availabilities"
    )


    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK
    )


    start_time = models.TimeField()

    end_time = models.TimeField()


    def clean(self):

        if self.start_time >= self.end_time:
            raise ValidationError(
                "La hora de inicio debe ser anterior a la hora final."
            )


    def is_available(self, check_datetime):

        return (
            self.day_of_week == check_datetime.weekday()
            and self.start_time <= check_datetime.time() <= self.end_time
        )


    def __str__(self):

        return (
            f"{self.resource} - "
            f"{self.get_day_of_week_display()} "
            f"{self.start_time}-{self.end_time}"
        )


    class Meta:

        verbose_name = "Disponibilidad"
        verbose_name_plural = "Disponibilidades"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "resource",
                    "day_of_week",
                    "start_time",
                    "end_time"
                ],
                name="unique_resource_availability"
            )
        ]



class RecurringBooking(models.Model):


    FREQUENCY_CHOICES = [
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
    ]


    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="recurring_bookings"
    )


    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name="recurring_reservations"
    )


    day_of_week = models.IntegerField(
        choices=Availability.DAYS_OF_WEEK,
        null=True,
        blank=True
    )


    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(31)
        ]
    )


    start_time = models.TimeField()

    end_time = models.TimeField()


    start_date = models.DateField()

    end_date = models.DateField()


    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default="weekly"
    )


    is_active = models.BooleanField(
        default=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    def clean(self):

        if not self.resource.is_active:
            raise ValidationError(
                "No se puede crear una reserva para una pista inactiva."
            )


        if self.start_date > self.end_date:
            raise ValidationError(
                "La fecha inicial debe ser anterior a la fecha final."
            )


        if self.start_time >= self.end_time:
            raise ValidationError(
                "La hora de inicio debe ser anterior a la hora final."
            )


        if self.frequency == "weekly":

            if self.day_of_week is None or self.day_of_month is not None:
                raise ValidationError(
                    "Selecciona un día de la semana (semanal) o un día del mes (mensual)."
                )

            if self.start_date.weekday() != self.day_of_week:
                raise ValidationError(
                    "La fecha inicial no coincide con el día seleccionado."
                )

        elif self.frequency == "monthly":

            if self.day_of_month is None or self.day_of_week is not None:
                raise ValidationError(
                    "Selecciona un día de la semana (semanal) o un día del mes (mensual)."
                )

            if self.start_date.day != self.day_of_month:
                raise ValidationError(
                    "La fecha inicial no coincide con el día seleccionado."
                )

        else:
            raise ValidationError(
                "Frecuencia de repetición no válida."
            )


    def __str__(self):

        if self.frequency == "monthly":
            return (
                f"{self.user} - "
                f"{self.resource} - "
                f"Día {self.day_of_month}"
            )

        return (
            f"{self.user} - "
            f"{self.resource} - "
            f"{self.get_day_of_week_display()}"
        )


    class Meta:

        verbose_name = "Reserva recurrente"
        verbose_name_plural = "Reservas recurrentes"

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        frequency="weekly",
                        day_of_week__isnull=False,
                        day_of_month__isnull=True
                    )
                    | models.Q(
                        frequency="monthly",
                        day_of_month__isnull=False,
                        day_of_week__isnull=True,
                        day_of_month__range=(1, 31)
                    )
                ),
                name="check_recurring_frequency_day"
            ),
            models.UniqueConstraint(
                fields=[
                    "resource",
                    "user",
                    "frequency",
                    "day_of_week",
                    "day_of_month",
                    "start_time",
                    "end_time",
                    "start_date",
                    "end_date"
                ],
                name="unique_recurring_booking"
            ),
            models.UniqueConstraint(
                fields=[
                    "resource",
                    "user",
                    "day_of_week",
                    "start_time",
                    "end_time",
                    "start_date",
                    "end_date"
                ],
                condition=models.Q(frequency="weekly"),
                name="unique_weekly_recurring"
            ),
            models.UniqueConstraint(
                fields=[
                    "resource",
                    "user",
                    "day_of_month",
                    "start_time",
                    "end_time",
                    "start_date",
                    "end_date"
                ],
                condition=models.Q(frequency="monthly"),
                name="unique_monthly_recurring"
            )
        ]



class Booking(models.Model):


    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Cancelado'),
    ]


    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="bookings"
    )


    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name="reservations"
    )


    recurring_booking = models.ForeignKey(
        RecurringBooking,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="generated_bookings"
    )


    start_date = models.DateTimeField()

    end_date = models.DateTimeField()


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="confirmed"
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )



    def clean(self):

        if not self.resource.is_active:
            raise ValidationError(
                "La pista no está disponible."
            )


        if self.start_date >= self.end_date:
            raise ValidationError(
                "La hora de inicio debe ser anterior a la hora final."
            )


        overlapping = Booking.objects.filter(
            resource=self.resource,
            start_date__lt=self.end_date,
            end_date__gt=self.start_date
        ).exclude(
            id=self.id
        )


        if overlapping.exists():
            raise ValidationError(
                "La pista ya está reservada en ese horario."
            )


        weekday = self.start_date.weekday()


        available = Availability.objects.filter(
            resource=self.resource,
            day_of_week=weekday,
            start_time__lte=self.start_date.time(),
            end_time__gte=self.end_date.time()
        )


        if not available.exists():
            raise ValidationError(
                "La pista no está disponible en ese horario."
            )



    def __str__(self):

        return (
            f"{self.resource} - "
            f"{self.user} - "
            f"{self.start_date}"
        )