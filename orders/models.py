from django.db import models
class Order(models.Model):
    table = models.ForeignKey(
        'tables.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Стол',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='new')

    def __str__(self):
        return f'Заказ №{self.pk}'
