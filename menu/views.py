from decimal import Decimal, InvalidOperation

from django.db.models import Count, Prefetch, ProtectedError, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ALLERGEN_NAMES, BADGES, Category, Dish
from .serializers import (
    CategorySerializer, DishDetailSerializer, DishListSerializer,
    DishWriteSerializer, MenuCategorySerializer,
)

MENU_MANAGERS = ['owner', 'admin', 'chef']
RESTAURANT_STAFF = ['owner', 'admin', 'chef', 'waiter']


def has_role(user, roles):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return getattr(user, 'role', None) in roles


def is_menu_manager(user):
    return has_role(user, MENU_MANAGERS)


class IsMenuManagerOrReadOnly(BasePermission):
    message = 'Менять меню могут только владелец, администратор и шеф-повар.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_menu_manager(request.user)


class IsRestaurantStaff(BasePermission):
    message = 'Только для сотрудников ресторана.'

    def has_permission(self, request, view):
        return has_role(request.user, RESTAURANT_STAFF)


def get_decimal_param(params, name):
    value = params.get(name)
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValidationError({name: 'Должно быть числом.'})



class CategoryViewSet(viewsets.ModelViewSet):

    serializer_class = CategorySerializer
    permission_classes = [IsMenuManagerOrReadOnly]
    lookup_field = 'slug'
    pagination_class = None

    def get_queryset(self):
        queryset = Category.objects.annotate(
            available_count=Count('dishes', filter=Q(dishes__is_available=True))
        )
        if not is_menu_manager(self.request.user):
            queryset = queryset.filter(is_active=True)
        return queryset

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'В категории есть блюда. Сначала перенесите или удалите их, либо скройте категорию.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['get'])
    def dishes(self, request, slug=None):
        category = self.get_object()
        dishes = category.dishes.select_related('category')
        if not (is_menu_manager(request.user) and request.query_params.get('all') == 'true'):
            dishes = dishes.filter(is_available=True)
        return Response(DishListSerializer(dishes, many=True, context={'request': request}).data)



class DishViewSet(viewsets.ModelViewSet):

    permission_classes = [IsMenuManagerOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'ingredients']
    ordering_fields = ['price', 'name', 'created_at', 'order']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DishWriteSerializer
        if self.action == 'retrieve':
            return DishDetailSerializer
        return DishListSerializer

    def get_queryset(self):
        queryset = Dish.objects.select_related('category')
        params = self.request.query_params
        manager = is_menu_manager(self.request.user)

        if not manager:
            queryset = queryset.filter(category__is_active=True)

        if self.action == 'list' and not (manager and params.get('all') == 'true'):
            queryset = queryset.filter(is_available=True)

        category = params.get('category')
        if category:
            if category.isdigit():
                queryset = queryset.filter(category_id=category)
            else:
                queryset = queryset.filter(category__slug=category)

        min_price = get_decimal_param(params, 'min_price')
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        max_price = get_decimal_param(params, 'max_price')
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

        badge_fields = {code: field for code, field, label in BADGES}
        for badge in params.get('badge', '').split(','):
            badge = badge.strip()
            if not badge:
                continue
            if badge not in badge_fields:
                raise ValidationError({'badge': f'Нет такого бейджа: {badge}. Есть: {", ".join(badge_fields)}.'})
            queryset = queryset.filter(**{badge_fields[badge]: True})

        for allergen in params.get('without', '').split(','):
            allergen = allergen.strip()
            if not allergen:
                continue
            if allergen not in ALLERGEN_NAMES:
                raise ValidationError({'without': f'Нет такого аллергена: {allergen}.'})
            queryset = queryset.exclude(allergens__regex=rf'(^|,){allergen}(,|$)')

        station = params.get('station')
        if station:
            queryset = queryset.filter(kitchen_station=station)
        return queryset

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'Блюдо уже есть в заказах, удалить нельзя. Поставьте его в стоп-лист.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'])
    def featured(self, request):
        dishes = Dish.objects.select_related('category').filter(
            is_featured=True, is_available=True, category__is_active=True,
        ).order_by('order', 'name')[:8]
        return Response(DishListSerializer(dishes, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'], url_path='stop-list', permission_classes=[IsRestaurantStaff])
    def stop_list(self, request):
        dishes = Dish.objects.select_related('category').filter(is_available=False)
        return Response(DishListSerializer(dishes, many=True, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='toggle-available')
    def toggle_available(self, request, pk=None):
        dish = self.get_object()
        dish.is_available = not dish.is_available
        dish.save(update_fields=['is_available', 'updated_at'])
        return Response(DishDetailSerializer(dish, context={'request': request}).data)



class MenuView(APIView):

    permission_classes = []

    def get(self, request):
        available_dishes = Dish.objects.filter(is_available=True).select_related('category')
        categories = Category.objects.filter(is_active=True).prefetch_related(
            Prefetch('dishes', queryset=available_dishes)
        )
        categories = [category for category in categories if len(category.dishes.all()) > 0]
        return Response(MenuCategorySerializer(categories, many=True, context={'request': request}).data)