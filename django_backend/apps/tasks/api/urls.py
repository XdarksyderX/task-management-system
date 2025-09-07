from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, TagViewSet, TaskTemplateViewSet

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="tasks")
router.register(r"tags", TagViewSet, basename="tags")
router.register(r"task-templates", TaskTemplateViewSet, basename="task-templates")

urlpatterns = [
    path("", include(router.urls)),
]
