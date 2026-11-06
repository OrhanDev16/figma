from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class PublicOrderThrottle(AnonRateThrottle):
    """Ограничение для гостей (по IP), защита от спама заказами."""
    scope = "public_orders"


class WaiterOrderThrottle(UserRateThrottle):
    scope = "waiter_orders"
