from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from .apiviews import RegisterAPIView, UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
    path("register/", csrf_exempt(RegisterAPIView.as_view())),
    path("login/", csrf_exempt(TokenObtainPairView.as_view())),
    path("refresh/", csrf_exempt(TokenRefreshView.as_view())),
    path("logout/", csrf_exempt(TokenBlacklistView.as_view())),
]
