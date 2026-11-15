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
from django.utils import timezone
from rest_framework import serializers

from .models import TABLE_STATUSES, Table


class TableSerializer(serializers.ModelSerializer):
    zone_display = serializers.CharField(source='get_zone_display', read_only=True)
    shape_display = serializers.CharField(source='get_shape_display', read_only=True)

    class Meta:
        model = Table
        fields = [
            'id', 'number', 'seats', 'zone', 'zone_display', 'shape', 'shape_display',
            'pos_x', 'pos_y', 'width', 'height', 'is_active', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_seats(self, value):
        if value < 1 or value > 20:
            raise serializers.ValidationError('Количество мест должно быть от 1 до 20.')
        return value

    def validate_pos_x(self, value):
        if value > 1000:
            raise serializers.ValidationError('Позиция X не может быть больше 1000.')
        return value

    def validate_pos_y(self, value):
        if value > 600:
            raise serializers.ValidationError('Позиция Y не может быть больше 600.')
        return value


class FloorPlanTableSerializer(serializers.ModelSerializer):
    """Стол на плане зала - со статусом и бронями."""
    zone_display = serializers.CharField(source='get_zone_display', read_only=True)
    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    current_reservation = serializers.SerializerMethodField()
    next_reservation = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = [
            'id', 'number', 'seats', 'zone', 'zone_display', 'shape',
            'pos_x', 'pos_y', 'width', 'height', 'is_active',
            'status', 'status_display', 'current_reservation', 'next_reservation',
        ]

    def get_moment(self):
        # время, на которое строим план (None - сейчас)
        return self.context.get('moment')

    def get_status(self, obj):
        return obj.get_status(self.get_moment())

    def get_status_display(self, obj):
        return TABLE_STATUSES[obj.get_status(self.get_moment())]

    def reservation_info(self, reservation):
        if reservation is None:
            return None
        start = timezone.localtime(reservation.starts_at)
        end = timezone.localtime(reservation.ends_at)
        return {
            'id': reservation.id,
            'guest_name': reservation.guest_name,
            'guest_phone': reservation.guest_phone,
            'guests_count': reservation.guests_count,
            'status': reservation.status,
            'time': start.strftime('%H:%M') + ' - ' + end.strftime('%H:%M'),
        }

    def get_current_reservation(self, obj):
        current = obj.get_current_reservation()
        moment = self.get_moment()
        if current and moment and not (current.starts_at <= moment < current.ends_at):
            return None
        return self.reservation_info(current)

    def get_next_reservation(self, obj):
        return self.reservation_info(obj.get_next_reservation(self.get_moment()))
