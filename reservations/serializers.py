import re
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from tables.models import Table

from .models import (
    DEFAULT_DURATION, LAST_BOOKING_TIME, OPEN_TIME,
    Reservation, ReservationHistory,
)


def make_datetime(date, time):
    return timezone.make_aware(datetime.combine(date, time.replace(second=0, microsecond=0)))


def check_phone(phone):
    phone = phone.strip()
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 9 or len(digits) > 15:
        raise serializers.ValidationError('Введите корректный номер телефона, например +996 555 123 456.')
    return phone


def check_guests_count(value):
    if value < 1:
        raise serializers.ValidationError('Минимум 1 гость.')
    if value > 30:
        raise serializers.ValidationError('Больше 30 гостей - только по телефону ресторана.')
    return value


class TableShortSerializer(serializers.ModelSerializer):
    zone_display = serializers.CharField(source='get_zone_display', read_only=True)

    class Meta:
        model = Table
        fields = ['id', 'number', 'seats', 'zone', 'zone_display']


class ReservationHistorySerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ReservationHistory
        fields = ['id', 'action', 'action_display', 'old_status', 'new_status',
                  'changes', 'comment', 'user', 'user_name', 'created_at']

    def get_user_name(self, obj):
        return str(obj.user) if obj.user else None


class ReservationListSerializer(serializers.ModelSerializer):
    table = TableShortSerializer(read_only=True)
    date = serializers.CharField(read_only=True)
    time = serializers.CharField(read_only=True)
    end_time = serializers.CharField(read_only=True)
    duration = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'guest_name', 'guest_phone', 'guests_count', 'date', 'time', 'end_time',
                  'duration', 'table', 'status', 'status_display', 'source', 'source_display', 'comment']


class ReservationDetailSerializer(ReservationListSerializer):
    history = ReservationHistorySerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta(ReservationListSerializer.Meta):
        fields = ReservationListSerializer.Meta.fields + [
            'guest_email', 'starts_at', 'ends_at', 'admin_comment', 'cancel_reason',
            'created_by', 'created_by_name', 'confirmed_at', 'seated_at', 'completed_at',
            'cancelled_at', 'created_at', 'updated_at', 'history',
        ]

    def get_created_by_name(self, obj):
        return str(obj.created_by) if obj.created_by else None



class ReservationCreateSerializer(serializers.ModelSerializer):
    date = serializers.DateField(write_only=True)
    time = serializers.TimeField(write_only=True)
    duration = serializers.IntegerField(write_only=True, required=False, default=DEFAULT_DURATION)
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Reservation
        fields = ['guest_name', 'guest_phone', 'guest_email', 'guests_count', 'date', 'time',
                  'duration', 'table', 'source', 'comment', 'admin_comment']

    def validate_guest_phone(self, value):
        return check_phone(value)

    def validate_guests_count(self, value):
        return check_guests_count(value)

    def validate_duration(self, value):
        if value < 30 or value > 360:
            raise serializers.ValidationError('Длительность от 30 до 360 минут.')
        return value

    def validate(self, attrs):
        starts_at = make_datetime(attrs.pop('date'), attrs.pop('time'))
        ends_at = starts_at + timedelta(minutes=attrs.pop('duration'))

        if starts_at < timezone.now() - timedelta(minutes=30):
            raise serializers.ValidationError({'time': 'Нельзя создать бронь на прошедшее время.'})
        if starts_at > timezone.now() + timedelta(days=60):
            raise serializers.ValidationError({'date': 'Бронировать можно максимум на 60 дней вперёд.'})

        table = attrs.get('table')
        if table:
            errors = Reservation.check_table(table, starts_at, ends_at, attrs['guests_count'])
            if errors:
                raise serializers.ValidationError({'table': errors})

        attrs['starts_at'] = starts_at
        attrs['ends_at'] = ends_at
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        reservation = Reservation.objects.create(
            status=Reservation.STATUS_CONFIRMED,
            confirmed_at=timezone.now(),
            created_by=user,
            **validated_data
        )
        reservation.add_history('created', user, old_status='')
        return reservation


class ReservationUpdateSerializer(serializers.ModelSerializer):
    date = serializers.DateField(write_only=True, required=False)
    time = serializers.TimeField(write_only=True, required=False)
    duration = serializers.IntegerField(write_only=True, required=False)
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Reservation
        fields = ['guest_name', 'guest_phone', 'guest_email', 'guests_count', 'date', 'time',
                  'duration', 'table', 'source', 'comment', 'admin_comment']

    def validate_guest_phone(self, value):
        return check_phone(value)

    def validate_guests_count(self, value):
        return check_guests_count(value)

    def validate_duration(self, value):
        if value < 30 or value > 360:
            raise serializers.ValidationError('Длительность от 30 до 360 минут.')
        return value

    def validate(self, attrs):
        reservation = self.instance
        if not reservation.is_active:
            raise serializers.ValidationError('Завершённую или отменённую бронь изменить нельзя.')

        date = attrs.pop('date', None)
        time = attrs.pop('time', None)
        duration = attrs.pop('duration', None)
        starts_at = reservation.starts_at
        ends_at = reservation.ends_at

        if date or time or duration:
            old_start = timezone.localtime(reservation.starts_at)
            starts_at = make_datetime(date or old_start.date(), time or old_start.time())
            ends_at = starts_at + timedelta(minutes=duration or reservation.duration)

            if reservation.status == Reservation.STATUS_SEATED and starts_at != reservation.starts_at:
                raise serializers.ValidationError({'time': 'Гость уже за столом, время начала менять нельзя.'})
            if starts_at != reservation.starts_at and starts_at < timezone.now() - timedelta(minutes=30):
                raise serializers.ValidationError({'time': 'Нельзя перенести бронь на прошедшее время.'})

            attrs['starts_at'] = starts_at
            attrs['ends_at'] = ends_at

        table = attrs['table'] if 'table' in attrs else reservation.table
        guests_count = attrs.get('guests_count', reservation.guests_count)
        if table:
            errors = Reservation.check_table(table, starts_at, ends_at, guests_count, exclude_id=reservation.id)
            if errors:
                raise serializers.ValidationError({'table': errors})
        return attrs

    def update(self, instance, validated_data):
        before = instance.get_snapshot()
        instance = super().update(instance, validated_data)
        after = instance.get_snapshot()

        changes = {}
        for key in before:
            if before[key] != after[key]:
                changes[key] = {'old': before[key], 'new': after[key]}
        if changes:
            instance.add_history('updated', self.context['request'].user, changes=changes)
        return instance



class PublicReservationSerializer(serializers.ModelSerializer):
    date = serializers.DateField(write_only=True)
    time = serializers.TimeField(write_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'guest_name', 'guest_phone', 'guest_email', 'guests_count', 'date', 'time', 'comment']
        read_only_fields = ['id']

    def validate_guest_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Укажите имя.')
        return value

    def validate_guest_phone(self, value):
        return check_phone(value)

    def validate_guests_count(self, value):
        return check_guests_count(value)

    def validate(self, attrs):
        date = attrs.pop('date')
        time = attrs.pop('time')
        starts_at = make_datetime(date, time)
        ends_at = starts_at + timedelta(minutes=DEFAULT_DURATION)

        if starts_at < timezone.now() + timedelta(minutes=30):
            raise serializers.ValidationError({'time': 'Выберите время минимум через 30 минут от текущего.'})
        if starts_at > timezone.now() + timedelta(days=60):
            raise serializers.ValidationError({'date': 'Бронировать можно максимум на 60 дней вперёд.'})
        if time < OPEN_TIME or time > LAST_BOOKING_TIME:
            raise serializers.ValidationError({
                'time': f'Бронирование с сайта с {OPEN_TIME.strftime("%H:%M")} до {LAST_BOOKING_TIME.strftime("%H:%M")}.'
            })

        free_count = Reservation.get_free_tables(starts_at, ends_at, attrs['guests_count']).count()
        waiting_count = Reservation.objects.filter(
            table__isnull=True,
            status__in=Reservation.ACTIVE_STATUSES,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        ).count()
        if free_count <= waiting_count:
            raise serializers.ValidationError({'time': 'На это время нет свободных столов, выберите другое время.'})

        attrs['starts_at'] = starts_at
        attrs['ends_at'] = ends_at
        return attrs

    def create(self, validated_data):
        reservation = Reservation.objects.create(
            source='website',
            status=Reservation.STATUS_PENDING,
            **validated_data
        )
        reservation.add_history('created', old_status='', comment='Заявка с сайта')
        return reservation

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'guest_name': instance.guest_name,
            'guests_count': instance.guests_count,
            'date': instance.date,
            'time': instance.time,
            'status': instance.status,
            'message': 'Спасибо! Заявка принята, администратор позвонит вам для подтверждения.',
        }



class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, error_messages={
        'required': 'Укажите причину отмены.',
        'blank': 'Укажите причину отмены.',
        'min_length': 'Причина слишком короткая.',
    })


class SeatSerializer(serializers.Serializer):
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all(), required=False)


class AssignTableSerializer(serializers.Serializer):
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all(), error_messages={
        'required': 'Укажите стол.',
        'does_not_exist': 'Такого стола нет.',
    })


class RescheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    time = serializers.TimeField()
    duration = serializers.IntegerField(required=False)
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all(), required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate_duration(self, value):
        if value < 30 or value > 360:
            raise serializers.ValidationError('Длительность от 30 до 360 минут.')
        return value