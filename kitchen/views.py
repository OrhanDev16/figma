from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import OrderItem
from .serializers import OrderItemSerializer


class KitchenQueueViewSet(viewsets.ModelViewSet):
  """ViewSet для управления очередью на кухне.

  Поддерживает фильтрацию по цеху (?workshop=ID) и сортировку по времени
  ожидания.
  """

  queryset = OrderItem.objects.exclude(
      status='served'
  ).order_by(  # Убираем уже отданные на раздачу
      'created_at'
  )  # Сначала самые старые (приоритет по времени)
  serializer_class = OrderItemSerializer
  filter_backends = [DjangoFilterBackend]
  filterset_fields = ['workshop', 'status']

  @action(detail=True, methods=['patch'], url_path='start-cooking')
  def start_cooking(self, request, pk=None):
    """Действие: Начать приготовление"""
    item = self.get_object()
    item.status = 'cooking'
    item.save()
    return Response(
        OrderItemSerializer(item).data, status=status.HTTP_200_OK
    )

  @action(detail=True, methods=['patch'], url_path='mark-ready')
  def mark_ready(self, request, pk=None):
    """Действие: Отметить готовым"""
    item = self.get_object()
    item.status = 'ready'
    item.save()
    return Response(
        OrderItemSerializer(item).data, status=status.HTTP_200_OK
    )

  @action(detail=True, methods=['patch'], url_path='transfer-to-service')
  def transfer_to_service(self, request, pk=None):
    """Действие: Передача на раздачу (для официанта)"""
    item = self.get_object()
    item.status = 'served'
    item.save()
    return Response(
        {'detail': 'Позиция передана на раздачу и уведена из очереди кухни.'},
        status=status.HTTP_200_OK,
    )