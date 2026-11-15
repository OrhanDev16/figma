from django.apps import AppConfig


class StoreAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store_app'

class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"
    verbose_name = "Заказы"
