import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .models import Resource


class HomeView(TemplateView):
    """Vista de la página de inicio del club."""
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resources"] = Resource.objects.filter(is_active=True)
        return context


class BookingView(LoginRequiredMixin, TemplateView):
    """Vista de reserva de pista."""
    template_name = "bookings/reserva.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resources = Resource.objects.filter(is_active=True)
        courts_json = []
        for r in resources:
            courts_json.append({
                "id": r.id,
                "name": r.name,
                "description": r.description or "",
                "type": r.court_type,
                "price": float(r.price_per_hour),
            })
        context["courts_json"] = json.dumps(courts_json, ensure_ascii=False)
        return context
