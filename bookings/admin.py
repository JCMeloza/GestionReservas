from django.contrib import admin
from .models import Resource, Availability, Booking, RecurringBooking


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

@admin.register(RecurringBooking)
class RecurringBookingAdmin(admin.ModelAdmin):
    list_display = (
        "resource",
        "user",
        "get_day",
        "day_of_month",
        "start_time",
        "end_time",
        "start_date",
        "end_date",
        "is_active",
    )

    list_filter = (
        "resource",
        "day_of_week",
        "is_active",
        "frequency",
    )

    def get_day(self, obj):
        if obj.frequency == "monthly":
            return obj.day_of_month
        return obj.get_day_of_week_display()

    get_day.short_description = "Día"