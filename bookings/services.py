"""Servicios de reservas: generación y consulta de slots libres.

Lógica pura y testeable, sin dependencias del request. Los datetimes
devueltos son timezone-aware (USE_TZ=True, timezone por defecto Europe/Madrid).
"""

from datetime import datetime, timedelta

from django.utils import timezone

# Duración de cada slot de reserva en minutos.
SLOT_MINUTES = 60


def _slot_end(start):
    return start + timedelta(minutes=SLOT_MINUTES)


def generate_free_slots(resource, date):
    """Devuelve los slots libres de `resource` para `date`.

    Cada slot es un dict ``{'start': datetime, 'end': datetime}``. Un slot es
    libre si: el bloque completo cae dentro de una Availability de ese día,
    aún no ha comenzado y no solapa con ninguna Booking no cancelada.
    """
    now = timezone.localtime()
    slots = []

    for availability in resource.availabilities.filter(day_of_week=date.weekday()):
        cursor = datetime.combine(date, availability.start_time)
        bound = datetime.combine(date, availability.end_time)

        # Solo bloques completos dentro del rango: si el final se pasa,
        # el bloque parcial se descarta (la condición del while lo corta).
        while _slot_end(cursor) <= bound:
            start = timezone.make_aware(cursor)
            end = _slot_end(start)
            cursor += timedelta(minutes=SLOT_MINUTES)

            if start <= now:
                continue

            overlapping = resource.bookings.filter(
                start_date__lt=end,
                end_date__gt=start,
            ).exclude(status="cancelled")

            if not overlapping.exists():
                slots.append({"start": start, "end": end})

    slots.sort(key=lambda slot: slot["start"])
    return slots


def is_slot_free(resource, start, end):
    """Indica si el rango [start, end) se puede reservar para `resource`.

    Mismo criterio que ``generate_free_slots``: pista activa, rango dentro de
    una Availability, en el futuro y sin solape con bookings no canceladas.
    """
    if not resource.is_active:
        return False

    if start >= end or start <= timezone.localtime():
        return False

    inside_availability = resource.availabilities.filter(
        day_of_week=start.weekday(),
        start_time__lte=start.time(),
        end_time__gte=end.time(),
    ).exists()
    if not inside_availability:
        return False

    overlapping = resource.bookings.filter(
        start_date__lt=end,
        end_date__gt=start,
    ).exclude(status="cancelled")

    return not overlapping.exists()
