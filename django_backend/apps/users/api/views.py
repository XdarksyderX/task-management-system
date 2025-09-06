from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from apps.users.models import Team
from .permissions import IsSelfOrAdmin
from .serializers import (
    UserSerializer, UserUpdateSerializer, RegisterSerializer,
    TeamSerializer, TeamCreateSerializer, MemberActionSerializer, TeamMembersSerializer
)

# Import Kafka event publishers
from ..producer import (
    publish_user_registered,
    publish_user_login,
    publish_user_logout,
    publish_user_login_failed,
    publish_team_created
)

User = get_user_model()

class RegisterAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    
    def perform_create(self, serializer):
        user = serializer.save()
        # Publish user registration event
        publish_user_registered(
            user.id,
            user.username,
            user.email,
            is_staff=user.is_staff,
            date_joined=user.date_joined.isoformat()
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view that sets JWT tokens in secure cookies with RSA signing"""
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # Handle login failure
        if response.status_code != 200:
            username = request.data.get('username', 'unknown')
            ip_address = self.get_client_ip(request)
            reason = 'Invalid credentials'
            publish_user_login_failed(username, ip_address, reason)
        
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
                
                # Publish user login event
                ip_address = self.get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                publish_user_login(user_id, username, ip_address, user_agent)
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
                getattr(settings, 'AUTH_COOKIE_ACCESS', 'access_token'),
                access_token,
                max_age=60 * 60 * 24,  # 1 day
                httponly=getattr(settings, 'AUTH_COOKIE_HTTPONLY', False),
                secure=getattr(settings, 'AUTH_COOKIE_SECURE', False),
                samesite=getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax')
            )
            
            new_response.set_cookie(
                getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token'),
                refresh_token,
                max_age=60 * 60 * 24 * 7,  # 7 days
                httponly=getattr(settings, 'AUTH_COOKIE_HTTPONLY', False),
                secure=getattr(settings, 'AUTH_COOKIE_SECURE', False),
                samesite=getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax')
            )
            
            return new_response
        
        return response


class CustomTokenBlacklistView(TokenBlacklistView):
    """Custom logout view that clears JWT cookies"""
    
    def post(self, request, *args, **kwargs):
        # Publish logout event if user is authenticated
        if request.user and request.user.is_authenticated:
            publish_user_logout(request.user.id, request.user.username)
        
        # Try to blacklist refresh token
        try:
            refresh_token = request.COOKIES.get(getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token'))
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass  # Token might be invalid, but we still want to clear cookies
        
        response = Response({'message': 'Logout successful'})
        
        # Clear cookies using settings configuration
        response.delete_cookie(getattr(settings, 'AUTH_COOKIE_ACCESS', 'access_token'))
        response.delete_cookie(getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token'))
        
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


class TeamViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Team.objects.all().order_by("-created_at")
        # Users can see teams they created or are members of
        return Team.objects.filter(
            models.Q(created_by=user) | models.Q(members=user)
        ).distinct().order_by("-created_at")
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TeamCreateSerializer
        return TeamSerializer
    
    def perform_create(self, serializer):
        team = serializer.save(created_by=self.request.user)
        # Automatically add creator as member
        team.add_member(self.request.user)
        # Publish team creation event
        publish_team_created(
            self.request.user.id,
            team.id,
            team.name,
            team.description
        )
    
    def destroy(self, request, *args, **kwargs):
        team = self.get_object()
        if not team.can_manage(request.user):
            return Response(
                {"error": "Only team admin can delete the team"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        team = self.get_object()
        if not team.can_manage(request.user):
            return Response(
                {"error": "Only team admin can update the team"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        """Add a member to the team"""
        team = self.get_object()
        
        if not team.can_manage(request.user):
            return Response(
                {"error": "Only team admin can add members"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MemberActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        user = User.objects.get(id=user_id)
        
        if team.is_member(user):
            return Response(
                {"error": "User is already a member of this team"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        team.add_member(user)
        return Response(
            {"message": f"User {user.username} added to team {team.name}"}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["post"])
    def remove_member(self, request, pk=None):
        """Remove a member from the team"""
        team = self.get_object()
        
        if not team.can_manage(request.user):
            return Response(
                {"error": "Only team admin can remove members"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MemberActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        user = User.objects.get(id=user_id)
        
        # Prevent admin from removing themselves
        if user == team.created_by:
            return Response(
                {"error": "Team admin cannot be removed from the team"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not team.is_member(user):
            return Response(
                {"error": "User is not a member of this team"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        team.remove_member(user)
        return Response(
            {"message": f"User {user.username} removed from team {team.name}"}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        """Leave the team (for non-admin members)"""
        team = self.get_object()
        user = request.user
        
        # Admin cannot leave their own team
        if team.is_admin(user):
            return Response(
                {"error": "Team admin cannot leave the team. Transfer ownership or delete the team instead."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not team.is_member(user):
            return Response(
                {"error": "You are not a member of this team"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        team.remove_member(user)
        return Response(
            {"message": f"You have left team {team.name}"}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["post"])
    def add_members(self, request, pk=None):
        """Add multiple members to the team"""
        team = self.get_object()
        
        if not team.can_manage(request.user):
            return Response(
                {"error": "Only team admin can add members"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = TeamMembersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_ids = serializer.validated_data['user_ids']
        users = User.objects.filter(id__in=user_ids)
        
        added_users = []
        already_members = []
        
        for user in users:
            if team.is_member(user):
                already_members.append(user.username)
            else:
                team.add_member(user)
                added_users.append(user.username)
        
        response_data = {}
        if added_users:
            response_data['added'] = added_users
        if already_members:
            response_data['already_members'] = already_members
            
        return Response(response_data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """Get team members"""
        team = self.get_object()
        members = team.members.all()
        serializer = UserSerializer(members, many=True)
        return Response(serializer.data)
