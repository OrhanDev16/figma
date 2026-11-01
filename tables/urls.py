from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, PublicOrderCreateView

router = DefaultRouter(trailing_slash=False)
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [

    path("orders/public", PublicOrderCreateView.as_view(), name="order-public-create"),
    path("", include(router.urls)),
]
