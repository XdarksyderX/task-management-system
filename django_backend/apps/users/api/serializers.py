from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.users.models import Team

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'display_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating User model"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'display_name', 'email']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for Team model"""
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    member_count = serializers.ReadOnlyField()
    members = UserSerializer(many=True, read_only=True)
    
    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'created_by', 'member_count', 'members']
        read_only_fields = ['id', 'created_by', 'member_count', 'members']
    
    def create(self, validated_data):
        # The created_by will be set in the view
        return super().create(validated_data)


class TeamCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating teams"""
    
    class Meta:
        model = Team
        fields = ['name', 'description']


class MemberActionSerializer(serializers.Serializer):
    """Serializer for adding/removing single members"""
    user_id = serializers.IntegerField()
    
    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        return value


class TeamMembersSerializer(serializers.Serializer):
    """Serializer for adding multiple members"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    
    def validate_user_ids(self, value):
        # Check that all users exist
        existing_users = User.objects.filter(id__in=value)
        if existing_users.count() != len(value):
            raise serializers.ValidationError("One or more users do not exist")
        return value
