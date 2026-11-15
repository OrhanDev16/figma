from django.contrib import admin, messages

from .models import Reservation, ReservationHistory


class ReservationHistoryInline(admin.TabularInline):
    model = ReservationHistory
    extra = 0
    can_delete = False
    fields = ['created_at', 'action', 'old_status', 'new_status', 'changes', 'comment', 'user']
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['id', 'guest_name', 'guest_phone', 'starts_at', 'guests_count', 'table', 'status', 'source']
    list_display_links = ['id', 'guest_name']
    list_filter = ['status', 'source', 'table__zone', 'starts_at']
    search_fields = ['guest_name', 'guest_phone', 'guest_email']
    date_hierarchy = 'starts_at'
    list_select_related = ['table']
    readonly_fields = ['created_by', 'confirmed_at', 'seated_at', 'completed_at', 'cancelled_at', 'created_at', 'updated_at']
    inlines = [ReservationHistoryInline]
    actions = ['confirm_selected', 'cancel_selected']
    fieldsets = (
        ('Гость', {'fields': ('guest_name', 'guest_phone', 'guest_email', 'guests_count', 'comment')}),
        ('Бронь', {'fields': ('starts_at', 'ends_at', 'table', 'status', 'source', 'admin_comment', 'cancel_reason')}),
        ('Служебное', {'fields': ('created_by', 'confirmed_at', 'seated_at', 'completed_at',
                                  'cancelled_at', 'created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Подтвердить выбранные заявки')
    def confirm_selected(self, request, queryset):
        count = 0
        for reservation in queryset.filter(status=Reservation.STATUS_PENDING):
            reservation.confirm(request.user)
            count += 1
        self.message_user(request, f'Подтверждено заявок: {count}', messages.SUCCESS)

    @admin.action(description='Отменить выбранные брони')
    def cancel_selected(self, request, queryset):
        count = 0
        for reservation in queryset.filter(status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED]):
            reservation.cancel('Отменено через админку', request.user)
            count += 1
        self.message_user(request, f'Отменено броней: {count}', messages.SUCCESS)


@admin.register(ReservationHistory)
class ReservationHistoryAdmin(admin.ModelAdmin):
    list_display = ['reservation', 'action', 'old_status', 'new_status', 'user', 'created_at']
    list_filter = ['action']
    search_fields = ['reservation__guest_name', 'reservation__guest_phone']

    def has_add_permission(self, request):
        return False