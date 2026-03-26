from django.urls import path

from .views import (
    home,
    workflow_create,
    workflow_edit,
    workflow_list,
    workflow_save,
    workflow_toggle_active,
    workflow_webhook,
)

urlpatterns = [
    path("", home, name="home"),
    path("workflows/", workflow_list, name="workflow_list"),
    path("workflows/new/", workflow_create, name="workflow_create"),
    path("workflows/<int:pk>/edit/", workflow_edit, name="workflow_edit"),
    path("workflows/<int:pk>/save/", workflow_save, name="workflow_save"),
    path("workflows/<int:pk>/toggle-active/", workflow_toggle_active, name="workflow_toggle_active"),
    path("hooks/<int:pk>/<str:token>/", workflow_webhook, name="workflow_webhook"),
]
