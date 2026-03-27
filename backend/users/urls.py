from django.urls import path

from .views import profile, send_confirmation_email

urlpatterns = [
    path("profile/", profile, name="profile"),
    path("profile/send-confirmation/", send_confirmation_email, name="send_confirmation_email"),
]

