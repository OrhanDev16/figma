from django.urls import path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    RegisterView,
    ProfileView,
    UserListView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)


urlpatterns = [

    # Регистрация
    path(
        'register/',
        RegisterView.as_view(),
        name='register'
    ),

    # Авторизация
    path(
        'login/',
        TokenObtainPairView.as_view(),
        name='login'
    ),

    # Обновление JWT токена
    path(
        'token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),

    # Профиль
    path(
        'profile/',
        ProfileView.as_view(),
        name='profile'
    ),

    # Список пользователей
    path(
        'users/',
        UserListView.as_view(),
        name='users'
    ),

    # Запрос сброса пароля
    path(
        'password-reset/',
        PasswordResetRequestView.as_view(),
        name='password_reset'
    ),

    # Подтверждение нового пароля
    path(
        'password-reset-confirm/',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),

]