from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, PublicOrderCreateView

router = DefaultRouter(trailing_slash=False)
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [

    path("orders/public", PublicOrderCreateView.as_view(), name="order-public-create"),
    path("", include(router.urls)),
]
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FloorPlanView, FreeTablesView, TableViewSet

router = DefaultRouter()
router.register('tables', TableViewSet, basename='tables')

urlpatterns = [
    path('floor-plan/', FloorPlanView.as_view(), name='floor-plan'),
    path('tables-free/', FreeTablesView.as_view(), name='tables-free'),
]

urlpatterns += router.urls
