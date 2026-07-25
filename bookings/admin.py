from django.contrib import admin
from .models import Resource, Availability, Booking


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
    )


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "resource",
        "day_of_week",
        "start_time",
        "end_time",
    )
    ordering = (
        "resource",
        "day_of_week",
        "start_time",
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "resource",
        "user",
        "start_date",
        "end_date",
        "status",
    )

    list_filter = (
        "status",
        "resource",
    )