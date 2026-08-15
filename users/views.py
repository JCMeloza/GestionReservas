from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView

from users.forms import CustomUserCreationForm


class RegisterView(CreateView):
    """Vista de registro de nuevos usuarios."""
    form_class = CustomUserCreationForm
    template_name = 'registration/registro.html'

    def get_success_url(self):
        return reverse('login')


class CustomLoginView(LoginView):
    """Vista de inicio de sesión con redirección según el perfil."""
    template_name = 'registration/login.html'

    def get_success_url(self):
        user = self.request.user

        if user.is_superuser:
            return reverse('admin:index')

        return reverse('home')


class CustomLogoutView(LogoutView):
    """Vista de cierre de sesión."""
    next_page = reverse_lazy('home')
