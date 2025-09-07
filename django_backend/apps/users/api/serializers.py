from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.users.models import Team

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "display_name"]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "display_name"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class TeamSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    member_count = serializers.ReadOnlyField()
    is_admin = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "description",
            "created_by",
            "members",
            "member_count",
            "created_at",
            "is_admin",
            "is_member",
        ]
        read_only_fields = ["created_by", "created_at"]

    def get_is_admin(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.is_admin(request.user)
        return False

    def get_is_member(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.is_member(request.user)
        return False


class TeamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["name", "description"]


class MemberActionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")


class TeamMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )

    def validate_user_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate user IDs are not allowed.")

        existing_users = User.objects.filter(id__in=value)
        if len(existing_users) != len(value):
            raise serializers.ValidationError("One or more users not found.")

        return value
