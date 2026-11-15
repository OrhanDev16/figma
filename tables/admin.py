from django.contrib import admin
from django.utils import timezone

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
from reservations.models import Reservation

from .models import Table


class TodayReservationsInline(admin.TabularInline):
    """Брони стола на сегодня и дальше."""
    model = Reservation
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ['guest_name', 'guest_phone', 'guests_count', 'starts_at', 'ends_at', 'status']
    readonly_fields = fields
    verbose_name = 'Бронь'
    verbose_name_plural = 'Ближайшие брони'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(starts_at__date__gte=timezone.localdate()).order_by('starts_at')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'zone', 'seats', 'shape', 'is_active', 'description']
    list_display_links = ['number']
    list_filter = ['zone', 'shape', 'is_active']
    list_editable = ['is_active']
    search_fields = ['description']
    ordering = ['number']
    inlines = [TodayReservationsInline]
    fieldsets = (
        ('Основное', {'fields': ('number', 'seats', 'zone', 'is_active', 'description')}),
        ('План зала', {'fields': ('shape', 'pos_x', 'pos_y', 'width', 'height')}),
    )
