from django .urls import path 
from .consumers import TaskCommentsConsumer 

websocket_urlpatterns =[
path ("ws/tasks/<int:task_id>/comments/",TaskCommentsConsumer .as_asgi ())
]
