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