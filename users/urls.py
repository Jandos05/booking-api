
from django.urls import path

from .views import RegisterView, LoginView, UserProfileView


urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/profile/", UserProfileView.as_view(), name="profile"),
]
