from django.contrib import admin

from .models import Order, OrderHistory, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["name", "unit_price"]


class OrderHistoryInline(admin.TabularInline):
    model = OrderHistory
    extra = 0
    can_delete = False
    readonly_fields = ["action", "actor", "from_value", "to_value", "comment", "created_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "table", "status", "source", "total_price", "created_at"]
    list_filter = ["status", "source"]
    inlines = [OrderItemInline, OrderHistoryInline]
