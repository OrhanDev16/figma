from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from tables.models import Table
from tables.views import IsHallStaff

from .models import DEFAULT_DURATION, LAST_BOOKING_TIME, OPEN_TIME, Reservation
from .serializers import (
    AssignTableSerializer, CancelSerializer, PublicReservationSerializer, RescheduleSerializer,
    ReservationCreateSerializer, ReservationDetailSerializer, ReservationHistorySerializer,
    ReservationListSerializer, ReservationUpdateSerializer, SeatSerializer, make_datetime,
)


class PublicReservationThrottle(AnonRateThrottle):
    rate = '10/hour'


def error(message, field='detail'):
    return Response({field: message}, status=status.HTTP_400_BAD_REQUEST)


def safe_date(value):
    try:
        return parse_date(value) if value else None
    except ValueError:
        return None


class ReservationViewSet(viewsets.ModelViewSet):

    queryset = Reservation.objects.select_related('table', 'created_by')
    permission_classes = [IsHallStaff]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['guest_name', 'guest_phone', 'guest_email']
    ordering_fields = ['starts_at', 'created_at', 'guests_count']
    ordering = ['starts_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'today':
            return ReservationListSerializer
        if self.action == 'create':
            return ReservationCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ReservationUpdateSerializer
        if self.action == 'cancel':
            return CancelSerializer
        if self.action == 'seat':
            return SeatSerializer
        if self.action == 'assign_table':
            return AssignTableSerializer
        if self.action == 'reschedule':
            return RescheduleSerializer
        if self.action == 'history':
            return ReservationHistorySerializer
        return ReservationDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        if params.get('date'):
            date = safe_date(params['date'])
            if date is None:
                return queryset.none()
            queryset = queryset.filter(starts_at__date=date)
        date_from = safe_date(params.get('date_from'))
        if date_from:
            queryset = queryset.filter(starts_at__date__gte=date_from)
        date_to = safe_date(params.get('date_to'))
        if date_to:
            queryset = queryset.filter(starts_at__date__lte=date_to)

        if params.get('status'):
            queryset = queryset.filter(status__in=params['status'].split(','))
        if params.get('source'):
            queryset = queryset.filter(source=params['source'])
        if params.get('table'):
            queryset = queryset.filter(table_id=params['table'])
        if params.get('zone'):
            queryset = queryset.filter(table__zone=params['zone'])
        if params.get('without_table') == 'true':
            queryset = queryset.filter(table__isnull=True)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        return Response(ReservationDetailSerializer(reservation).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        reservation = self.get_object()
        serializer = self.get_serializer(reservation, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        return Response(ReservationDetailSerializer(reservation).data)


    @action(detail=False, methods=['get'])
    def today(self, request):
        # все брони на сегодня, кроме отменённых
        reservations = self.get_queryset().filter(starts_at__date=timezone.localdate()).exclude(status='cancelled')
        return Response(ReservationListSerializer(reservations, many=True).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        # сводка на день: ?date=2026-11-05 (по умолчанию сегодня)
        if request.query_params.get('date'):
            day = safe_date(request.query_params['date'])
        else:
            day = timezone.localdate()
        if day is None:
            return error('Неверная дата, нужен формат ГГГГ-ММ-ДД.', 'date')

        reservations = Reservation.objects.filter(starts_at__date=day)
        result = {'date': day, 'total': reservations.count(), 'guests': 0, 'without_table': 0}
        for value, label in Reservation.STATUS_CHOICES:
            result[value] = reservations.filter(status=value).count()
        for reservation in reservations.filter(status__in=Reservation.ACTIVE_STATUSES):
            result['guests'] += reservation.guests_count
            if reservation.table is None:
                result['without_table'] += 1
        return Response(result)


    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status != Reservation.STATUS_PENDING:
            return error(f'Подтвердить можно только новую заявку, сейчас статус «{reservation.get_status_display()}».', 'status')
        reservation.confirm(request.user)
        return Response(ReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=['post'])
    def seat(self, request, pk=None):
        # гость пришёл
        reservation = self.get_object()
        if reservation.status not in [Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED]:
            return error(f'Нельзя отметить приход, статус брони «{reservation.get_status_display()}».', 'status')
        if timezone.localtime(reservation.starts_at).date() != timezone.localdate():
            return error('Отметить приход можно только в день брони.', 'status')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        table = serializer.validated_data.get('table') or reservation.table
        if table is None:
            return error('Укажите стол, за который садится гость.', 'table')

        errors = Reservation.check_table(table, reservation.starts_at, reservation.ends_at,
                                         reservation.guests_count, exclude_id=reservation.id)
        current = table.get_current_reservation()
        if current and current.id != reservation.id:
            errors.append(f'За столом №{table.number} сейчас сидят гости ({current.guest_name}).')
        if errors:
            return error(errors, 'table')

        reservation.seat(table, request.user)
        return Response(ReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        # гости ушли, стол освободился
        reservation = self.get_object()
        if reservation.status != Reservation.STATUS_SEATED:
            return error('Завершить можно только бронь, где гость уже за столом.', 'status')
        reservation.complete(request.user)
        return Response(ReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=['post'], url_path='no-show')
    def no_show(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status not in [Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED]:
            return error(f'Нельзя, статус брони «{reservation.get_status_display()}».', 'status')
        if timezone.now() < reservation.starts_at:
            return error(f'Время брони ещё не наступило ({reservation.time}).', 'status')
        reservation.mark_no_show(request.user)
        return Response(ReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status not in [Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED]:
            return error(f'Отменить нельзя, статус брони «{reservation.get_status_display()}».', 'status')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation.cancel(serializer.validated_data['reason'], request.user)
        return Response(ReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        # перенос на другое время, стол можно оставить или поменять
        reservation = self.get_object()
        if reservation.status not in [Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED]:
            return error(f'Перенести нельзя, статус брони «{reservation.get_status_display()}».', 'status')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        starts_at = make_datetime(data['date'], data['time'])
        ends_at = starts_at + timedelta(minutes=data.get('duration') or reservation.duration)
        if starts_at < timezone.now() - timedelta(minutes=30):
            return error('Нельзя перенести на прошедшее время.', 'time')

        if 'table' in data:
            table = data['table']
        else:
            table = reservation.table

        if table:
            errors = Reservation.check_table(table, starts_at, ends_at, reservation.guests_count, exclude_id=reservation.id)
            if errors:
                return error(errors, 'table')

        before = reservation.get_snapshot()
        reservation.starts_at = starts_at
        reservation.ends_at = ends_at
        reservation.table = table
        reservation.save()
        after = reservation.get_snapshot()

        changes = {}
        for key in before:
            if before[key] != after[key]:
                changes[key] = {'old': before[key], 'new': after[key]}
        reservation.add_history('rescheduled', request.user, changes=changes, comment=data.get('comment', ''))
        return Response(ReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=['post'], url_path='assign-table')
    def assign_table(self, request, pk=None):
        # назначить стол или пересадить гостей за другой
        reservation = self.get_object()
        if not reservation.is_active:
            return error(f'Нельзя, статус брони «{reservation.get_status_display()}».', 'status')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        table = serializer.validated_data['table']

        errors = Reservation.check_table(table, reservation.starts_at, reservation.ends_at,
                                         reservation.guests_count, exclude_id=reservation.id)
        if reservation.status == Reservation.STATUS_SEATED:
            current = table.get_current_reservation()
            if current and current.id != reservation.id:
                errors.append(f'За столом №{table.number} сейчас сидят гости ({current.guest_name}).')
        if errors:
            return error(errors, 'table')

        old_table = reservation.table.number if reservation.table else None
        reservation.table = table
        reservation.save()
        reservation.add_history('table_assigned', request.user,
                                changes={'table': {'old': old_table, 'new': table.number}})
        return Response(ReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        reservation = self.get_object()
        history = reservation.history.select_related('user')
        return Response(ReservationHistorySerializer(history, many=True).data)


class PublicReservationView(generics.CreateAPIView):
    """Заявка на бронь с сайта. Создаётся со статусом pending, без стола."""
    serializer_class = PublicReservationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PublicReservationThrottle]


class FreeTimeView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        day = safe_date(request.query_params.get('date'))
        if day is None:
            return error('Укажите дату в формате ГГГГ-ММ-ДД.', 'date')
        guests = request.query_params.get('guests', '2')
        if not guests.isdigit() or int(guests) < 1:
            return error('Количество гостей должно быть числом.', 'guests')
        guests = int(guests)

        slots = []
        current = datetime.combine(day, OPEN_TIME)
        last = datetime.combine(day, LAST_BOOKING_TIME)
        earliest = timezone.now() + timedelta(minutes=30)
        has_tables = Table.objects.filter(is_active=True, seats__gte=guests).exists()

        while current <= last:
            starts_at = timezone.make_aware(current)
            ends_at = starts_at + timedelta(minutes=DEFAULT_DURATION)
            available = False
            if has_tables and starts_at >= earliest:
                free_count = Reservation.get_free_tables(starts_at, ends_at, guests).count()
                waiting_count = Reservation.objects.filter(
                    table__isnull=True,
                    status__in=Reservation.ACTIVE_STATUSES,
                    starts_at__lt=ends_at,
                    ends_at__gt=starts_at,
                ).count()
                available = free_count > waiting_count
            slots.append({'time': current.strftime('%H:%M'), 'available': available})
            current += timedelta(minutes=30)

        return Response({'date': day, 'guests': guests, 'slots': slots})