from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from .permissions import IsSelfOrAdmin
from .serializers import UserSerializer, UserUpdateSerializer, RegisterSerializer

User = get_user_model()

class RegisterAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view that sets JWT tokens in secure cookies"""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Get tokens from response data
            access_token = response.data['access']
            refresh_token = response.data['refresh']
            
            # Get user from token payload
            from rest_framework_simplejwt.tokens import UntypedToken
            from jwt import decode as jwt_decode
            from rest_framework_simplejwt.settings import api_settings
            from django.http import JsonResponse
            
            try:
                decoded_data = jwt_decode(
                    access_token, 
                    api_settings.SIGNING_KEY, 
                    algorithms=[api_settings.ALGORITHM]
                )
                user_id = decoded_data.get('user_id')
                user = User.objects.get(id=user_id)
                username = user.username
            except Exception:
                username = None
            
            # Get redirect URL from next parameter or default to dashboard
            next_url = request.data.get('next') or request.GET.get('next', '/dashboard/')
            
            # Check if request wants JSON response (for API calls)
            accept_header = request.headers.get('Accept', '')
            if 'application/json' in accept_header or request.content_type == 'application/json':
                # Create JSON response for API calls
                new_response = Response({
                    'message': 'Login successful',
                    'user': username,
                    'redirect_url': next_url,
                    'success': True
                })
            else:
                # Create redirect response for form submissions
                from django.http import HttpResponseRedirect
                new_response = HttpResponseRedirect(next_url)
            
            # Set secure cookies on the response
            new_response.set_cookie(
                'access_token',
                access_token,
                max_age=60 * 60 * 24,  # 1 day
                httponly=True,
                secure=getattr(settings, 'SESSION_COOKIE_SECURE', False),
                samesite='Strict'
            )
            
            new_response.set_cookie(
                'refresh_token',
                refresh_token,
                max_age=60 * 60 * 24 * 7,  # 7 days
                httponly=True,
                secure=getattr(settings, 'SESSION_COOKIE_SECURE', False),
                samesite='Strict'
            )
            
            return new_response
        
        return response


class CustomTokenBlacklistView(TokenBlacklistView):
    """Custom logout view that clears JWT cookies"""
    
    def post(self, request, *args, **kwargs):
        # Try to blacklist refresh token
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass  # Token might be invalid, but we still want to clear cookies
        
        response = Response({'message': 'Logout successful'})
        
        # Clear cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        return response

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [permissions.IsAuthenticated(), IsSelfOrAdmin()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)
