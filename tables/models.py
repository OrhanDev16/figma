from datetime import timedelta

from django.db import models
from django.utils import timezone


TABLE_STATUSES = {
    'free': 'Свободен',
    'reserved': 'Забронирован',
    'occupied': 'Занят',
    'unavailable': 'Недоступен',
}

RESERVED_BEFORE_MINUTES = 60


class Table(models.Model):
    ZONE_CHOICES = (
        ('main_hall', 'Основной зал'),
        ('terrace', 'Терраса'),
        ('vip', 'VIP зал'),
        ('bar', 'Барная зона'),
    )
    SHAPE_CHOICES = (
        ('round', 'Круглый'),
        ('square', 'Квадратный'),
        ('rectangle', 'Прямоугольный'),
    )

    number = models.PositiveIntegerField(unique=True, verbose_name='Номер стола')
    seats = models.PositiveIntegerField(default=2, verbose_name='Количество мест')
    zone = models.CharField(max_length=20, choices=ZONE_CHOICES, default='main_hall', verbose_name='Зона')
    shape = models.CharField(max_length=20, choices=SHAPE_CHOICES, default='square', verbose_name='Форма')

    # координаты и размер стола на плане зала (холст 1000x600)
    pos_x = models.PositiveIntegerField(default=0, verbose_name='Позиция X')
    pos_y = models.PositiveIntegerField(default=0, verbose_name='Позиция Y')
    width = models.PositiveIntegerField(default=100, verbose_name='Ширина')
    height = models.PositiveIntegerField(default=100, verbose_name='Высота')

    is_active = models.BooleanField(default=True, verbose_name='Активен')
    description = models.CharField(max_length=255, blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Изменён')

    class Meta:
        ordering = ['number']
        verbose_name = 'Стол'
        verbose_name_plural = 'Столы'

    def __str__(self):
        return f'Стол №{self.number} ({self.seats} мест)'

    def get_current_reservation(self):
        return self.reservations.filter(status='seated').order_by('starts_at').first()

    def get_next_reservation(self, moment=None):
        if moment is None:
            moment = timezone.now()
        day = timezone.localtime(moment).date()
        return self.reservations.filter(
            status__in=['pending', 'confirmed'],
            starts_at__date=day,
            ends_at__gt=moment,
        ).order_by('starts_at').first()

    def get_status(self, moment=None):
        if not self.is_active:
            return 'unavailable'

        check_time = moment or timezone.now()

        current = self.get_current_reservation()
        if current:
            if moment is None or current.starts_at <= check_time < current.ends_at:
                return 'occupied'

        next_reservation = self.get_next_reservation(check_time)
        if next_reservation:
            if next_reservation.starts_at - timedelta(minutes=RESERVED_BEFORE_MINUTES) <= check_time:
                return 'reserved'

        return 'free'

    def is_free(self, starts_at, ends_at, exclude_id=None):
        from reservations.models import Reservation
        return not Reservation.get_conflicts(self, starts_at, ends_at, exclude_id).exists()

    def get_reservations_for_day(self, day):
        return self.reservations.filter(starts_at__date=day).order_by('starts_at')