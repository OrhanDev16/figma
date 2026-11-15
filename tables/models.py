from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
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


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        ACCEPTED = "accepted", "Принят"
        PREPARING = "preparing", "Готовится"
        READY = "ready", "Готов"
        SERVED = "served", "Подан"
        PAID = "paid", "Оплачен"
        CANCELLED = "cancelled", "Отменён"

    class Source(models.TextChoices):
        PUBLIC = "public", "Гость (QR/сайт)"
        WAITER = "waiter", "Официант"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Наличные"
        CARD = "card", "Карта"
        ONLINE = "online", "Онлайн"

    CLOSED_STATUSES = (Status.PAID, Status.CANCELLED)

    table = models.ForeignKey(
        "tables.Table", on_delete=models.PROTECT, related_name="orders"
    )
    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    source = models.CharField(max_length=10, choices=Source.choices)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.NEW, db_index=True
    )
    customer_name = models.CharField(max_length=100, blank=True)
    comment = models.TextField(blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    cancel_reason = models.TextField(blank=True)
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, blank=True
    )
    paid_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["table", "status"])]

    def __str__(self):
        return f"Заказ #{self.pk} ({self.get_status_display()})"

    @property
    def is_closed(self) -> bool:
        return self.status in self.CLOSED_STATUSES


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        "menu.MenuItem", on_delete=models.PROTECT, related_name="+"
    )
    # Снимок на момент заказа — цена/название в меню потом могут измениться
    name = models.CharField(max_length=200)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    comment = models.CharField(max_length=255, blank=True)

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.name} x{self.quantity}"


class OrderHistory(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Создан"
        STATUS_CHANGED = "status_changed", "Смена статуса"
        TABLE_CHANGED = "table_changed", "Перенос на другой стол"
        CANCELLED = "cancelled", "Отмена"
        PAID = "paid", "Оплата"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=20, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )  # null = гость
    from_value = models.CharField(max_length=100, blank=True)
    to_value = models.CharField(max_length=100, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name_plural = "order history"
    def get_reservations_for_day(self, day):
        return self.reservations.filter(starts_at__date=day).order_by('starts_at')
