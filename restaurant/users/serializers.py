from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import User


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'password',
            'password2',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password': 'Пароли не совпадают'
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')

        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.role = User.ROLE_CHOICES.waiter
        user.save()

        return user


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
            'created_at',
        ]

        read_only_fields = ['id', 'role', 'created_at']


class PasswordResetRequestSerializer(serializers.Serializer):

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):

    token = serializers.CharField()

    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                'new_password': 'Пароли не совпадают'
            })

        return attrs