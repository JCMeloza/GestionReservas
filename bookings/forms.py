from datetime import datetime

from django import forms

from bookings.models import Booking, Resource
from bookings.services import generate_free_slots


class BookingForm(forms.ModelForm):
    """Formulario de reserva puntual: pista + fecha + slot ('HH:MM').

    El Booking con sus datetimes se construye en la vista: aquí no se ejecuta
    ``Booking.clean()`` (aún no existen start/end) y la validación cruzada de
    solape/disponibilidad se resuelve contra los slots regenerados en el
    servidor con ``generate_free_slots``. Nunca se confía en el cliente.
    """

    date = forms.DateField(
        label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    slot = forms.CharField(
        label="Horario",
        max_length=5,
    )

    class Meta:
        model = Booking
        fields = ["resource", "date", "slot"]
        labels = {"resource": "Pista"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resource"].queryset = (
            Resource.objects.filter(is_active=True).order_by("name")
        )

    def _post_clean(self):
        # No se construye un Booking con datetimes en el form: la validación
        # cruzada (solape/disponibilidad) se hace en clean() contra services.
        pass

    def clean(self):
        cleaned = super().clean()
        resource = cleaned.get("resource")
        date = cleaned.get("date")
        slot = cleaned.get("slot")

        if not (resource and date and slot):
            return cleaned

        try:
            datetime.strptime(slot, "%H:%M")
        except ValueError:
            self.add_error("slot", "El horario seleccionado no es válido.")
            return cleaned

        free_slots = generate_free_slots(resource, date)
        free_keys = {s["start"].strftime("%H:%M") for s in free_slots}

        if slot not in free_keys:
            self.add_error(
                "slot",
                "El horario seleccionado ya no está disponible. "
                "Elige un horario de la lista.",
            )

        return cleaned
