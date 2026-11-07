from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.utils import timezone

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

from .permissions import IsAdminOrOwner


User = get_user_model()


class RegisterView(generics.CreateAPIView):

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class ProfileView(generics.RetrieveUpdateAPIView):

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrOwner]


class PasswordResetRequestView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = PasswordResetRequestSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        user = User.objects.filter(
            email=email,
            is_active=True
        ).first()

        if user:
            token = signing.dumps(
                {'user_id': user.pk},
                salt='restaurant-password-reset'
            )

            reset_link = (
                f"{settings.FRONTEND_URL}/reset-password"
                f"?token={token}"
            )

            send_mail(
                subject='Сброс пароля',
                message=(
                    f'Для сброса пароля перейдите по ссылке: '
                    f'{reset_link}\n'
                    f'Ссылка действительна 30 минут.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )

        return Response({
            'message': (
                'Если аккаунт с таким email существует, '
                'инструкция будет отправлена на почту.'
            )
        })


class PasswordResetConfirmView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = PasswordResetConfirmSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']

        try:
            data = signing.loads(
                token,
                salt='restaurant-password-reset',
                max_age=1800
            )

            user = User.objects.get(
                pk=data['user_id'],
                is_active=True
            )

        except (
            signing.BadSignature,
            signing.SignatureExpired,
            User.DoesNotExist,
            KeyError,
            TypeError,
        ):
            return Response(
                {'error': 'Ссылка недействительна или истекла'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(
            serializer.validated_data['new_password']
        )

        user.save()

        return Response({
            'message': 'Пароль успешно изменён'
        })
