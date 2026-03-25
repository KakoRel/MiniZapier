from django.urls import path

from .views import (
    home,
    workflow_create,
    workflow_edit,
    workflow_list,
    workflow_save,
)

urlpatterns = [
    path("", home, name="home"),
    path("workflows/", workflow_list, name="workflow_list"),
    path("workflows/new/", workflow_create, name="workflow_create"),
    path("workflows/<int:pk>/edit/", workflow_edit, name="workflow_edit"),
    path("workflows/<int:pk>/save/", workflow_save, name="workflow_save"),
]
