from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterAPIView, UserViewSet, TeamViewSet, CustomTokenObtainPairView, CustomTokenBlacklistView

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(r"teams", TeamViewSet, basename="teams")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/register/", csrf_exempt(RegisterAPIView.as_view())),
    path("auth/login/", csrf_exempt(CustomTokenObtainPairView.as_view())),
    path("auth/refresh/", csrf_exempt(TokenRefreshView.as_view())),
    path("auth/logout/", csrf_exempt(CustomTokenBlacklistView.as_view())),
]
