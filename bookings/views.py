from django.views.generic import TemplateView

from .models import Resource


class HomeView(TemplateView):
    """Vista de la página de inicio del club."""
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resources"] = Resource.objects.filter(is_active=True)
        return context
