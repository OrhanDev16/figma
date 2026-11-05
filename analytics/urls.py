from django.urls import path
from . import views

urlpatterns = [
    path("overview/", views.OverviewView.as_view()),
    path("sales-by-hour/", views.SalesByHourView.as_view()),
    path("sources/", views.SourcesView.as_view()),
    path("popular-dishes/", views.PopularDishesView.as_view()),
]