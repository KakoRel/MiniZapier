from django.urls import path

from .views import execution_detail, executions_list

urlpatterns = [
    path("", executions_list, name="executions_list"),
    path("<int:execution_id>/", execution_detail, name="execution_detail"),
]

