from django.urls import path
from . import views

urlpatterns = [
    path("analytics/overview/", views.OverviewView.as_view()),
    path("analytics/", views.AnalyticsView.as_view()),
]