from django.urls import path

from .views import analytics, execution_detail, execution_resume, executions_list

urlpatterns = [
    path("", executions_list, name="executions_list"),
    path("analytics/", analytics, name="analytics"),
    path("<int:execution_id>/resume/", execution_resume, name="execution_resume"),
    path("<int:execution_id>/", execution_detail, name="execution_detail"),
]

