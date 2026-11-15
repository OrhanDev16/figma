from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, DishViewSet, MenuView

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='categories')
router.register('dishes', DishViewSet, basename='dishes')

urlpatterns = [
    path('menu/', MenuView.as_view(), name='menu'),
]

urlpatterns += router.urls