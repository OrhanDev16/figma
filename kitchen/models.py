from django.db import models


class Workshop(models.Model):
  """Цех (например: Горячий, Холодный, Бар)"""

  name = models.CharField(max_length=100, unique=True, verbose_name='Название цеха')

  def __str__(self):
    return self.name


class OrderItem(models.Model):
  """Позиция внутри заказа (блюдо)"""

  STATUS_CHOICES = [
      ('new', 'Новый'),
      ('cooking', 'Готовится'),
      ('ready', 'Готов'),
      ('served', 'Передано на раздачу'),
  ]

  # Связь с общим заказом (предполагаем, что модель Order уже есть или создается в другом приложении)
  # Если модели Order нет, можно временно ссылаться на строку или стандартную модель
  order = models.ForeignKey(
      'orders.Order',
      on_delete=models.CASCADE,
      related_name='items',
      verbose_name='Заказ',
  )
  dish_name = models.CharField(max_length=255, verbose_name='Название блюда')
  quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
  workshop = models.ForeignKey(
      Workshop,
      on_delete=models.PROTECT,
      related_name='items',
      verbose_name='Цех',
  )
  status = models.CharField(
      max_length=20,
      choices=STATUS_CHOICES,
      default='new',
      verbose_name='Статус',
  )
  created_at = models.DateTimeField(
      auto_now_add=True, verbose_name='Время создания заказа'
  )
  updated_at = models.DateTimeField(
      auto_now=True, verbose_name='Время обновления статуса'
  )

  class Meta:
    verbose_name = 'Позиция заказа (Кухня)'
    verbose_name_plural = 'Позиции заказов (Кухня)'
    ordering = [
        'created_at'
    ]  # Сортировка по времени ожидания (сначала старые)

  def __str__(self):
    return f'{self.dish_name} (Кол-во: {self.quantity}) — [{self.get_status_display()}]'
