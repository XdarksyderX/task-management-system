from django.urls import path
from .consumers import TaskCommentsConsumer, TaskRoomConsumer, NotificationConsumer

websocket_urlpatterns = [
    path("ws/tasks/<int:task_id>/comments/", TaskCommentsConsumer.as_asgi()),
    path("ws/tasks/<int:task_id>/", TaskRoomConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
