from __future__ import annotations

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from .views import ExecutionViewSet, UserVariableViewSet, WorkflowViewSet

router = DefaultRouter()
router.register(r"workflows", WorkflowViewSet, basename="workflow")
router.register(r"executions", ExecutionViewSet, basename="execution")
router.register(r"variables", UserVariableViewSet, basename="variable")

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_schema"), name="api_docs"),
    path("", include(router.urls)),
]

