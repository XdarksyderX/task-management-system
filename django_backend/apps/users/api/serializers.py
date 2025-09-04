from django.contrib.auth import get_user_model
from rest_framework import serializers
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id","username","email","first_name","last_name","display_name"]

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email","first_name","last_name","display_name"]

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    class Meta:
        model = User
        fields = ["username","email","password"]
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
