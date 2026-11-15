from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FreeTimeView, PublicReservationView, ReservationViewSet

router = DefaultRouter()
router.register('reservations', ReservationViewSet, basename='reservations')

urlpatterns = [
    path('reservations/public/', PublicReservationView.as_view(), name='reservation-public'),
    path('reservations/free-time/', FreeTimeView.as_view(), name='reservation-free-time'),
]

urlpatterns += router.urls