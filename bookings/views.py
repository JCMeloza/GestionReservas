from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Vista de la página de inicio del club."""
    template_name = "home.html"
