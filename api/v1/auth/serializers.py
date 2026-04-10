from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.users.models import Users


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)
    telegram_id = serializers.CharField(required=False)

    def validate(self, attrs):
        login = attrs.get("login")
        password = attrs.get("password")
        print(login, password)
        try:
            user = Users.objects.get(username=login)
        except Users.DoesNotExist:
            raise serializers.ValidationError("Invalid login or password")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid login or password")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        attrs['user'] = user
        return attrs

    def to_representation(self, instance):
        user = self.validated_data['user']
        return {
            "id": user.id,
            "login": user.username,
            "role": user.role,
        }
