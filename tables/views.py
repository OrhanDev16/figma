from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from . import services
from .models import Order
from .serializers import (
    CancelOrderSerializer,
    MoveOrderSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    PayOrderSerializer,
    PublicOrderCreateSerializer,
    PublicOrderSerializer,
    WaiterOrderCreateSerializer,
)
from .throttles import PublicOrderThrottle, WaiterOrderThrottle


class PublicOrderCreateView(CreateAPIView):

    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # не требуем токен/CSRF
    throttle_classes = [PublicOrderThrottle]
    serializer_class = PublicOrderCreateSerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        order = services.create_order(
            table=d["table"],
            items=d["items"],
            source=Order.Source.PUBLIC,
            customer_name=d.get("customer_name", ""),
            comment=d.get("comment", ""),
        )
        return Response(PublicOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST   /orders               — заказ от официанта
    GET    /orders               — список (?status=&table=&mine=1&source=)
    GET    /orders/{id}          — детали с историей
    POST   /orders/{id}/move     — перенос на другой стол
    POST   /orders/{id}/cancel   — отмена с причиной
    POST   /orders/{id}/pay      — приём оплаты
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [WaiterOrderThrottle]

    def get_queryset(self):
        qs = Order.objects.select_related("table", "waiter").prefetch_related("items", "history")
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("table"):
            qs = qs.filter(table_id=p["table"])
        if p.get("source"):
            qs = qs.filter(source=p["source"])
        if p.get("mine") == "1":
            qs = qs.filter(waiter=self.request.user)
        return qs

    def get_serializer_class(self):
        return {
            "list": OrderListSerializer,
            "create": WaiterOrderCreateSerializer,
            "move": MoveOrderSerializer,
            "cancel": CancelOrderSerializer,
            "pay": PayOrderSerializer,
        }.get(self.action, OrderDetailSerializer)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        order = services.create_order(
            table=d["table"],
            items=d["items"],
            source=Order.Source.WAITER,
            waiter=request.user,
            customer_name=d.get("customer_name", ""),
            comment=d.get("comment", ""),
        )
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)

    def _respond(self, order):
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order = services.move_order(
            self.get_object(), new_table=ser.validated_data["table"], actor=request.user
        )
        return self._respond(order)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order = services.cancel_order(
            self.get_object(), reason=ser.validated_data["reason"], actor=request.user
        )
        return self._respond(order)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order = services.pay_order(
            self.get_object(),
            method=ser.validated_data["method"],
            amount=ser.validated_data["amount"],
            actor=request.user,
        )
        return self._respond(order)
