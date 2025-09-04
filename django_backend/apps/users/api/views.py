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
from .permissions import IsSelfOrAdmin, IsTeamAdmin
from .serializers import (
    UserSerializer, UserUpdateSerializer, RegisterSerializer,
    TeamSerializer, TeamCreateSerializer, MemberActionSerializer, TeamMembersSerializer
)

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


class TeamViewSet(viewsets.ModelViewSet):
    """ViewSet for Team model with member management"""
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return teams where user is a member"""
        return Team.objects.filter(members=self.request.user)
    
    def get_permissions(self):
        """Customize permissions based on action"""
        if self.action in ['update', 'partial_update', 'destroy', 'add_member', 'remove_member', 'add_members']:
            return [permissions.IsAuthenticated(), IsTeamAdmin()]
        return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        """Create team with current user as admin and add them as member"""
        team = serializer.save(created_by=self.request.user)
        team.members.add(self.request.user)
        return team
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a member to the team"""
        team = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user in team.members.all():
            return Response(
                {'error': 'User is already a member'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        team.members.add(user)
        return Response({'message': 'Member added successfully'})
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Remove a member from the team"""
        team = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user == team.created_by:
            return Response(
                {'error': 'Cannot remove team admin'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user not in team.members.all():
            return Response(
                {'error': 'User is not a member'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        team.members.remove(user)
        return Response({'message': 'Member removed successfully'})
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave the team (for non-admin members)"""
        team = self.get_object()
        user = request.user
        
        if user == team.created_by:
            return Response(
                {'error': 'Team admin cannot leave the team'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user not in team.members.all():
            return Response(
                {'error': 'You are not a member of this team'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        team.members.remove(user)
        return Response({'message': 'Left team successfully'})
    
    @action(detail=True, methods=['post'])
    def add_members(self, request, pk=None):
        """Add multiple members to the team"""
        team = self.get_object()
        
        # Handle both JSON and form data
        if isinstance(request.data, dict) and 'user_ids' in request.data:
            user_ids = request.data.get('user_ids', [])
            if not isinstance(user_ids, list):
                user_ids = [user_ids]
        else:
            # Handle form data
            user_ids = request.data.getlist('user_ids') if hasattr(request.data, 'getlist') else []
        
        if not user_ids:
            return Response(
                {'error': 'user_ids is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        added_users = []
        errors = []
        
        for user_id in user_ids:
            try:
                user = User.objects.get(id=int(user_id))
                
                if user not in team.members.all():
                    team.members.add(user)
                    added_users.append(user.username)
                else:
                    errors.append(f'User {user.username} is already a member')
            except (User.DoesNotExist, ValueError):
                errors.append(f'User with id {user_id} not found')
        
        return Response({
            'message': f'Added {len(added_users)} members',
            'added_users': added_users,
            'errors': errors
        })
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List team members"""
        team = self.get_object()
        members = team.members.all()
        members_data = [
            {
                'id': member.id,
                'username': member.username,
                'first_name': member.first_name,
                'last_name': member.last_name,
                'email': member.email,
                'is_admin': member == team.created_by
            }
            for member in members
        ]
        return Response({
            'members': members_data,
            'count': len(members_data)
        })
