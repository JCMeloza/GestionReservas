from django.urls import path

from users.views import CustomLoginView, CustomLogoutView, RegisterView

urlpatterns = [
    path('registro/', RegisterView.as_view(), name='registro'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
]
