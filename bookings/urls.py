from django.urls import path

from bookings.views import (
    BookingCreateView,
    CancelBookingView,
    MyBookingsView,
    ResourceListView,
)

urlpatterns = [
    path("pistas/", ResourceListView.as_view(), name="pistas"),
    path("reservar/", BookingCreateView.as_view(), name="reservar"),
    path("mis-reservas/", MyBookingsView.as_view(), name="mis-reservas"),
    path(
        "reservas/<int:pk>/cancelar/",
        CancelBookingView.as_view(),
        name="cancelar-reserva",
    ),
]
