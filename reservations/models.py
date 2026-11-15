from datetime import time, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

DEFAULT_DURATION = 120         # сколько длится бронь по умолчанию (минуты)
CLEANING_TIME = 15             # время на уборку стола между бронями (минуты)
OPEN_TIME = time(10, 0)        # с сайта можно бронировать с 10:00
LAST_BOOKING_TIME = time(22, 0)  # последняя бронь с сайта в 22:00


class Reservation(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_SEATED = 'seated'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_NO_SHOW = 'no_show'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Новая заявка'),
        (STATUS_CONFIRMED, 'Подтверждена'),
        (STATUS_SEATED, 'Гость пришёл'),
        (STATUS_COMPLETED, 'Завершена'),
        (STATUS_CANCELLED, 'Отменена'),
        (STATUS_NO_SHOW, 'Гость не пришёл'),
    )

    SOURCE_CHOICES = (
        ('website', 'Сайт'),
        ('phone', 'Телефон'),
        ('walk_in', 'Без брони'),
        ('other', 'Другое'),
    )
    ACTIVE_STATUSES = [STATUS_PENDING, STATUS_CONFIRMED, STATUS_SEATED]

    guest_name = models.CharField(max_length=100, verbose_name='Имя гостя')
    guest_phone = models.CharField(max_length=20, verbose_name='Телефон')
    guest_email = models.EmailField(blank=True, verbose_name='Email')
    guests_count = models.PositiveIntegerField(verbose_name='Количество гостей')

    starts_at = models.DateTimeField(verbose_name='Начало')
    ends_at = models.DateTimeField(verbose_name='Окончание')
    table = models.ForeignKey(
        'tables.Table', on_delete=models.PROTECT, null=True, blank=True,
        related_name='reservations', verbose_name='Стол',
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='Статус')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='phone', verbose_name='Источник')
    comment = models.TextField(blank=True, verbose_name='Пожелания гостя')
    admin_comment = models.TextField(blank=True, verbose_name='Заметка администратора')
    cancel_reason = models.TextField(blank=True, verbose_name='Причина отмены')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_reservations', verbose_name='Кто создал',
    )
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='Когда подтвердили')
    seated_at = models.DateTimeField(null=True, blank=True, verbose_name='Когда гость пришёл')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Когда завершили')
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='Когда отменили')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Изменена')

    class Meta:
        ordering = ['starts_at']
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'

    def __str__(self):
        return f'#{self.id} {self.guest_name} - {self.date} {self.time}'

    @property
    def date(self):
        return timezone.localtime(self.starts_at).strftime('%Y-%m-%d')

    @property
    def time(self):
        return timezone.localtime(self.starts_at).strftime('%H:%M')

    @property
    def end_time(self):
        return timezone.localtime(self.ends_at).strftime('%H:%M')

    @property
    def duration(self):
        return int((self.ends_at - self.starts_at).total_seconds() // 60)

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES


    @classmethod
    def get_conflicts(cls, table, starts_at, ends_at, exclude_id=None):
        cleaning = timedelta(minutes=CLEANING_TIME)
        conflicts = cls.objects.filter(
            table=table,
            status__in=cls.ACTIVE_STATUSES,
            starts_at__lt=ends_at + cleaning,
            ends_at__gt=starts_at - cleaning,
        )
        if exclude_id:
            conflicts = conflicts.exclude(id=exclude_id)
        return conflicts

    @classmethod
    def check_table(cls, table, starts_at, ends_at, guests_count, exclude_id=None):
        errors = []
        if not table.is_active:
            errors.append(f'Стол №{table.number} сейчас недоступен.')
        if guests_count and guests_count > table.seats:
            errors.append(f'За стол №{table.number} помещается {table.seats} чел., а гостей {guests_count}.')

        conflict = cls.get_conflicts(table, starts_at, ends_at, exclude_id).first()
        if conflict:
            errors.append(
                f'Стол №{table.number} занят: бронь #{conflict.id} ({conflict.guest_name}) '
                f'{conflict.date} с {conflict.time} до {conflict.end_time}. '
                f'Между бронями нужно {CLEANING_TIME} минут на уборку.'
            )
        return errors

    @classmethod
    def get_free_tables(cls, starts_at, ends_at, guests_count, exclude_id=None):
        from tables.models import Table

        cleaning = timedelta(minutes=CLEANING_TIME)
        busy = cls.objects.filter(
            status__in=cls.ACTIVE_STATUSES,
            table__isnull=False,
            starts_at__lt=ends_at + cleaning,
            ends_at__gt=starts_at - cleaning,
        )
        if exclude_id:
            busy = busy.exclude(id=exclude_id)
        busy_ids = busy.values_list('table_id', flat=True)

        return Table.objects.filter(is_active=True, seats__gte=guests_count).exclude(id__in=busy_ids).order_by('seats', 'number')

    def get_snapshot(self):
        return {
            'guest_name': self.guest_name,
            'guest_phone': self.guest_phone,
            'guests_count': self.guests_count,
            'date': self.date,
            'time': self.time,
            'end_time': self.end_time,
            'table': self.table.number if self.table else None,
            'comment': self.comment,
            'admin_comment': self.admin_comment,
        }

    def add_history(self, action, user=None, old_status=None, changes=None, comment=''):
        if user is not None and not user.is_authenticated:
            user = None
        ReservationHistory.objects.create(
            reservation=self,
            action=action,
            old_status=self.status if old_status is None else old_status,
            new_status=self.status,
            changes=changes or {},
            comment=comment,
            user=user,
        )

    def confirm(self, user=None):
        old_status = self.status
        self.status = self.STATUS_CONFIRMED
        self.confirmed_at = timezone.now()
        self.save()
        self.add_history('confirmed', user, old_status)

    def seat(self, table, user=None):
        old_status = self.status
        old_table = self.table.number if self.table else None
        self.table = table
        self.status = self.STATUS_SEATED
        self.seated_at = timezone.now()
        if not self.confirmed_at:
            self.confirmed_at = self.seated_at
        self.save()
        changes = {}
        if old_table != table.number:
            changes['table'] = {'old': old_table, 'new': table.number}
        self.add_history('seated', user, old_status, changes)

    def complete(self, user=None):
        old_status = self.status
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.save()
        self.add_history('completed', user, old_status)

    def cancel(self, reason, user=None):
        old_status = self.status
        self.status = self.STATUS_CANCELLED
        self.cancel_reason = reason
        self.cancelled_at = timezone.now()
        self.save()
        self.add_history('cancelled', user, old_status, comment=reason)

    def mark_no_show(self, user=None):
        old_status = self.status
        self.status = self.STATUS_NO_SHOW
        self.save()
        self.add_history('no_show', user, old_status)


class ReservationHistory(models.Model):
    ACTION_CHOICES = (
        ('created', 'Создана'),
        ('updated', 'Изменена'),
        ('confirmed', 'Подтверждена'),
        ('table_assigned', 'Назначен стол'),
        ('rescheduled', 'Перенесена'),
        ('seated', 'Гость пришёл'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
        ('no_show', 'Гость не пришёл'),
    )

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='history', verbose_name='Бронь')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Действие')
    old_status = models.CharField(max_length=20, blank=True, verbose_name='Статус до')
    new_status = models.CharField(max_length=20, blank=True, verbose_name='Статус после')
    changes = models.JSONField(default=dict, blank=True, verbose_name='Изменения')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reservation_actions', verbose_name='Сотрудник',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Когда')

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'История брони'
        verbose_name_plural = 'История бронирований'

    def __str__(self):
        return f'#{self.reservation_id} - {self.get_action_display()}'