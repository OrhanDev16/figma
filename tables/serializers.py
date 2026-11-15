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