from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import UserSerializer, UserUpdateSerializer, RegisterSerializer
User = get_user_model()

class RegisterAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["update","partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)
