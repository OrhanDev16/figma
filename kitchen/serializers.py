from rest_framework import serializers
from django.utils import timezone
from .models import OrderItem, Workshop



class WorkshopSerializer(serializers.ModelSerializer):

  class Meta:
    model = Workshop
    fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
  workshop_name = serializers.ReadOnlyField(source='workshop.name')
  waiting_time = serializers.SerializerMethodField(
      label="Время ожидания",
      help_text="Сколько минут позиция ждёт в очереди",
  )

  class Meta:
    model = OrderItem
    fields = [
        'id',
        'order',
        'dish_name',
        'quantity',
        'workshop',
        'workshop_name',
        'status',
        'created_at',
        'waiting_time',
    ]
    read_only_fields = ['created_at', 'waiting_time']

  def get_waiting_time(self, obj):

    delta = timezone.now() - obj.created_at
    return int(delta.total_seconds() // 60)