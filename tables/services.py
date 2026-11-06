from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Order, OrderHistory, OrderItem

def _log(order, action, actor=None, from_value="", to_value="", comment=""):
    OrderHistory.objects.create(
        order=order,
        action=action,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        from_value=str(from_value),
        to_value=str(to_value),
        comment=comment,
    )


def _lock(order: Order) -> Order:
    return Order.objects.select_for_update().select_related("table").get(pk=order.pk)


def _ensure_open(order: Order):
    if order.is_closed:
        raise ValidationError(
            f"Заказ уже в статусе «{order.get_status_display()}», изменить его нельзя."
        )


@transaction.atomic
def create_order(*, table, items, source, waiter=None, customer_name="", comment=""):

    order = Order.objects.create(
        table=table,
        waiter=waiter,
        source=source,
        customer_name=customer_name,
        comment=comment,
    )
    total = Decimal("0")
    rows = []
    for row in items:
        menu_item = row["menu_item"]
        qty = row["quantity"]
        rows.append(
            OrderItem(
                order=order,
                menu_item=menu_item,
                name=menu_item.name,
                unit_price=menu_item.price,  # серверная цена
                quantity=qty,
                comment=row.get("comment", ""),
            )
        )
        total += menu_item.price * qty
    OrderItem.objects.bulk_create(rows)
    order.total_price = total
    order.save(update_fields=["total_price", "updated_at"])
    _log(order, OrderHistory.Action.CREATED, actor=waiter, to_value=order.status)
    return order


@transaction.atomic
def move_order(order, *, new_table, actor):
    order = _lock(order)
    _ensure_open(order)
    if order.table_id == new_table.pk:
        raise ValidationError("Заказ уже находится за этим столом.")
    old = order.table
    order.table = new_table
    order.save(update_fields=["table", "updated_at"])
    _log(
        order,
        OrderHistory.Action.TABLE_CHANGED,
        actor=actor,
        from_value=old,
        to_value=new_table,
    )
    return order


@transaction.atomic
def cancel_order(order, *, reason, actor):
    order = _lock(order)
    _ensure_open(order)
    old_status = order.status
    order.status = Order.Status.CANCELLED
    order.cancel_reason = reason
    order.save(update_fields=["status", "cancel_reason", "updated_at"])
    _log(
        order,
        OrderHistory.Action.CANCELLED,
        actor=actor,
        from_value=old_status,
        to_value=order.status,
        comment=reason,
    )
    return order


@transaction.atomic
def pay_order(order, *, method, amount, actor):
    order = _lock(order)
    _ensure_open(order)
    if amount != order.total_price:
        raise ValidationError(
            {"amount": f"Сумма оплаты должна быть равна {order.total_price}."}
        )
    old_status = order.status
    order.status = Order.Status.PAID
    order.payment_method = method
    order.paid_amount = amount
    order.paid_at = timezone.now()
    order.save(
        update_fields=["status", "payment_method", "paid_amount", "paid_at", "updated_at"]
    )
    _log(
        order,
        OrderHistory.Action.PAID,
        actor=actor,
        from_value=old_status,
        to_value=order.status,
        comment=f"{method}: {amount}",
    )
    return order
