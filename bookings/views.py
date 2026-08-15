from datetime import datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, ListView, TemplateView

from bookings.forms import BookingForm
from bookings.models import Booking, Resource
from bookings.services import SLOT_MINUTES, generate_free_slots


class HomeView(TemplateView):
    """Vista de la página de inicio del club."""
    template_name = "home.html"


class ResourceListView(ListView):
    """Listado público de pistas activas."""
    model = Resource
    template_name = "bookings/resource_list.html"
    context_object_name = "resources"
    queryset = Resource.objects.filter(is_active=True).order_by("name")


class BookingCreateView(LoginRequiredMixin, FormView):
    """Reserva puntual: pista + fecha + slot libre."""
    form_class = BookingForm
    template_name = "bookings/booking_form.html"
    success_url = reverse_lazy("mis-reservas")

    def get_initial(self):
        """Preselecciona pista y fecha desde los query params en GET."""
        initial = super().get_initial()
        if self.request.method == "GET":
            resource_id = self.request.GET.get("resource")
            date = self.request.GET.get("date")
            if resource_id:
                initial["resource"] = resource_id
            if date:
                initial["date"] = date
        return initial

    def _get_selection(self):
        """Resuelve (resource, date) desde POST (formulario) o GET (params)."""
        raw_resource = self.request.POST.get("resource") or self.request.GET.get("resource")
        raw_date = self.request.POST.get("date") or self.request.GET.get("date")

        resource = None
        if raw_resource:
            try:
                resource = Resource.objects.filter(
                    pk=int(raw_resource),
                    is_active=True,
                ).first()
            except (TypeError, ValueError):
                resource = None

        date = None
        if raw_date:
            try:
                date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                date = None

        return resource, date

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resource, date = self._get_selection()
        if resource and date:
            context["slots"] = generate_free_slots(resource, date)
        else:
            context["slots"] = None
        return context

    def form_valid(self, form):
        resource = form.cleaned_data["resource"]
        date = form.cleaned_data["date"]
        slot = form.cleaned_data["slot"]

        # Regeneramos los slots en el servidor: nunca confiamos en el cliente.
        free_slots = generate_free_slots(resource, date)
        free_keys = {s["start"].strftime("%H:%M") for s in free_slots}

        if slot not in free_keys:
            form.add_error(
                "slot",
                "El horario seleccionado ya no está disponible. "
                "Elige un horario de la lista.",
            )
            return self.form_invalid(form)

        start_time = datetime.strptime(slot, "%H:%M").time()
        start = timezone.make_aware(datetime.combine(date, start_time))
        end = start + timedelta(minutes=SLOT_MINUTES)

        Booking.objects.create(
            user=self.request.user,
            resource=resource,
            start_date=start,
            end_date=end,
            status="confirmed",
        )
        return super().form_valid(form)


class MyBookingsView(LoginRequiredMixin, ListView):
    """Reservas del usuario logueado, separadas en próximas y pasadas."""
    template_name = "bookings/booking_list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        return (
            Booking.objects
            .filter(user=self.request.user)
            .select_related("resource")
            .order_by("-start_date")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context["now"] = now
        bookings = context["bookings"]
        context["upcoming"] = [
            b for b in bookings
            if b.start_date >= now and b.status != "cancelled"
        ]
        context["past"] = [
            b for b in bookings
            if b.start_date < now or b.status == "cancelled"
        ]
        return context


class CancelBookingView(LoginRequiredMixin, View):
    """Cancela una reserva propia que aún no ha comenzado (POST-only)."""
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        booking = get_object_or_404(Booking, pk=kwargs["pk"])

        if booking.user != request.user:
            raise PermissionDenied("No puedes cancelar una reserva ajena.")

        if booking.start_date > timezone.now():
            booking.status = "cancelled"
            booking.save()

        return redirect("mis-reservas")
