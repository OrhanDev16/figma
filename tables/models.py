from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


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
