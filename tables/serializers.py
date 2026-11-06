from rest_framework import serializers

from menu.models import MenuItem
from tables.models import Table

from .models import Order, OrderHistory, OrderItem


class OrderItemInputSerializer(serializers.Serializer):
    menu_item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=50)
    comment = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_menu_item(self, item):
        if not getattr(item, "is_available", True):
            raise serializers.ValidationError(f"«{item.name}» сейчас недоступно.")
        return item


class BaseOrderCreateSerializer(serializers.Serializer):
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all())
    items = OrderItemInputSerializer(many=True, allow_empty=False, max_length=50)
    customer_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate_table(self, table):
        if not getattr(table, "is_active", True):
            raise serializers.ValidationError("Этот стол недоступен.")
        return table


class PublicOrderCreateSerializer(BaseOrderCreateSerializer):
    pass


class WaiterOrderCreateSerializer(BaseOrderCreateSerializer):
    pass


class MoveOrderSerializer(serializers.Serializer):
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all())

    def validate_table(self, table):
        if not getattr(table, "is_active", True):
            raise serializers.ValidationError("Этот стол недоступен.")
        return table


class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, min_length=3)


class PayOrderSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "menu_item", "name", "unit_price", "quantity", "comment", "line_total"]


class OrderHistorySerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = OrderHistory
        fields = ["id", "action", "action_display", "actor", "from_value", "to_value", "comment", "created_at"]


class PublicOrderSerializer(serializers.ModelSerializer):
    """Что видит гость после оформления — без служебных данных."""
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "table", "status", "total_price", "items", "created_at"]


class OrderListSerializer(serializers.ModelSerializer):
    table_name = serializers.CharField(source="table.__str__", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "table", "table_name", "waiter", "source", "status", "status_display",
            "customer_name", "total_price", "items_count", "created_at",
        ]


class OrderDetailSerializer(OrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    history = OrderHistorySerializer(many=True, read_only=True)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + [
            "comment", "cancel_reason", "payment_method", "paid_amount", "paid_at",
            "updated_at", "items", "history",
        ]
