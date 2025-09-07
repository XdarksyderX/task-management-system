import os 
from django .core .asgi import get_asgi_application 
from channels .routing import ProtocolTypeRouter ,URLRouter 
from channels .auth import AuthMiddlewareStack 

os .environ .setdefault ("DJANGO_SETTINGS_MODULE","django_backend.settings")

django_asgi_app =get_asgi_application ()

from apps .tasks .websockets import routing as tasks_routing 
from apps .common .middleware import CookieJWTWebSocketMiddleware 

application =ProtocolTypeRouter (
{
"http":django_asgi_app ,
"websocket":CookieJWTWebSocketMiddleware (
URLRouter (
tasks_routing .websocket_urlpatterns 
)
),
}
)