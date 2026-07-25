from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.

class Resource(models.Model):
    name = models.CharField(
        max_length = 50,
        unique = True
    )
    description = models.TextField(
        blank = True,
        null = True
    )
    is_active = models.BooleanField(
        default = True
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
        on_delete = models.CASCADE,
        related_name="availabilities"
    )
    
    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK
    )

    start_time = models.TimeField()    
    end_time = models.TimeField()
    
    def is_available(self, check_datetime):
        return (
            self.day_of_week == check_datetime.weekday()
            and self.start_time <= check_datetime.time() <= self.end_time
        )
    
    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(
                "La hora de inicio debe ser anterior a la hora final."
            )

    def __str__(self):
        return f"{self.resource} de {self.get_day_of_week_display()}  {self.start_time}-{self.end_time}"

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

class Booking(models.Model):
    
    resource = models.ForeignKey(
        Resource, 
        on_delete = models.CASCADE,
        related_name="bookings"
    )
    
    user = models.ForeignKey(
        'users.User', 
        on_delete = models.CASCADE,
        related_name="reservations",
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(
        max_length = 20,
        choices = [
            ('pending', 'Pendiente'),
            ('confirmed', 'Confirmado'),
            ('cancelled', 'Cancelado'),
        ],
        default = 'pending'
    )

    created_at = models.DateTimeField( auto_now_add=True)
    updated_at = models.DateTimeField(auto_now = True)

    def clean(self):
        # 1. Comprobar que la fecha de inicio es anterior al final
        if self.start_date >= self.end_date:
            raise ValidationError(
                "La hora de inicio debe ser anterior a la hora final."
            )

        # 2. Comprobar solapamientos
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

        # 3. Comprobar disponibilidad semanal
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
        # Comprobar si la pista esta activa    
        if not self.resource.is_active:
            raise ValidationError("La pista no está disponible.")

    def __str__(self):
        return f"{self.resource} - {self.user} - {self.start_date}"

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
        related_name="recurring_bookings"
    )

    day_of_week = models.IntegerField(
        choices=Availability.DAYS_OF_WEEK
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    start_date = models.DateField()

    end_date = models.DateField()

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='weekly'
    )

    is_active = models.BooleanField(
        default=True
    )


    def __str__(self):
        return f"{self.user} - {self.resource} - {self.get_day_of_week_display()}"