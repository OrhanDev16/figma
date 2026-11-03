from datetime import datetime, timedelta

from django.db.models import ProtectedError
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TABLE_STATUSES, Table
from .serializers import FloorPlanTableSerializer, TableSerializer



class IsHallStaff(BasePermission):
    message = 'Недостаточно прав.'
    allowed_roles = ['owner', 'admin', 'waiter']

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return getattr(user, 'role', None) in self.allowed_roles


class IsManager(IsHallStaff):
    allowed_roles = ['owner', 'admin']


def get_date_param(request, name='date', required=True):
    value = request.query_params.get(name)
    if not value:
        if required:
            return None, f'Параметр {name} обязателен (формат ГГГГ-ММ-ДД).'
        return None, None
    try:
        day = parse_date(value)
    except ValueError:
        day = None
    if day is None:
        return None, f'Неверная дата в параметре {name}, нужен формат ГГГГ-ММ-ДД.'
    return day, None


def get_time_param(request, name='time'):
    value = request.query_params.get(name)
    try:
        result = parse_time(value) if value else None
    except ValueError:
        result = None
    if result is None:
        return None, f'Неверное время в параметре {name}, нужен формат ЧЧ:ММ.'
    return result, None


class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer

    def get_permissions(self):
        # смотреть столы могут все сотрудники зала, менять - только владелец и админ
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'toggle_active']:
            return [IsManager()]
        return [IsHallStaff()]

    def get_queryset(self):
        queryset = Table.objects.all()
        zone = self.request.query_params.get('zone')
        is_active = self.request.query_params.get('is_active')
        min_seats = self.request.query_params.get('min_seats')

        if zone:
            queryset = queryset.filter(zone=zone)
        if is_active in ['true', 'false']:
            queryset = queryset.filter(is_active=(is_active == 'true'))
        if min_seats and min_seats.isdigit():
            queryset = queryset.filter(seats__gte=int(min_seats))
        return queryset

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'У стола есть бронирования, удалить нельзя. Сделайте его неактивным.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        # включить / выключить стол (например, стол убрали на ремонт)
        table = self.get_object()
        table.is_active = not table.is_active
        table.save()
        return Response(TableSerializer(table).data)

    @action(detail=True, methods=['get'])
    def reservations(self, request, pk=None):
        # брони этого стола на день: ?date=2026-11-05 (по умолчанию сегодня)
        from reservations.serializers import ReservationListSerializer

        table = self.get_object()
        day, error = get_date_param(request, required=False)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        if day is None:
            day = timezone.localdate()

        reservations = table.get_reservations_for_day(day)
        return Response({
            'table': TableSerializer(table).data,
            'date': day,
            'reservations': ReservationListSerializer(reservations, many=True).data,
        })



class FloorPlanView(APIView):
    permission_classes = [IsHallStaff]

    def get(self, request):
        moment = None
        if request.query_params.get('date') or request.query_params.get('time'):
            day, error = get_date_param(request)
            if error:
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
            clock, error = get_time_param(request)
            if error:
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
            moment = timezone.make_aware(datetime.combine(day, clock))

        tables = Table.objects.all()
        zone = request.query_params.get('zone')
        if zone:
            tables = tables.filter(zone=zone)

        data = FloorPlanTableSerializer(tables, many=True, context={'moment': moment}).data

        # сколько столов в каждом статусе
        summary = {}
        for key in TABLE_STATUSES:
            summary[key] = len([t for t in data if t['status'] == key])

        return Response({
            'time': timezone.localtime(moment or timezone.now()),
            'zones': [{'value': value, 'label': label} for value, label in Table.ZONE_CHOICES],
            'summary': summary,
            'tables': data,
        })


class FreeTablesView(APIView):

    permission_classes = [IsHallStaff]

    def get(self, request):
        from reservations.models import DEFAULT_DURATION, Reservation

        day, error = get_date_param(request)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        clock, error = get_time_param(request)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        guests = request.query_params.get('guests', '1')
        duration = request.query_params.get('duration', str(DEFAULT_DURATION))
        if not guests.isdigit() or not duration.isdigit():
            return Response({'detail': 'guests и duration должны быть числами.'}, status=status.HTTP_400_BAD_REQUEST)

        starts_at = timezone.make_aware(datetime.combine(day, clock))
        ends_at = starts_at + timedelta(minutes=int(duration))
        tables = Reservation.get_free_tables(starts_at, ends_at, int(guests))
        return Response(TableSerializer(tables, many=True).data)