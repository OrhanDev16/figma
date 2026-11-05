from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class OverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "revenue": 125000,
            "orders_count": 48,
            "average_check": 2604,
            "vs_yesterday_percent": 12.5,
        })


class SalesByHourView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([
            {"hour": 12, "revenue": 8000, "orders": 4},
            {"hour": 13, "revenue": 15000, "orders": 7},
        ])


class SourcesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([
            {"source": "waiter", "orders": 30},
            {"source": "website", "orders": 18},
        ])


class PopularDishesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([
            {"dish": "Пицца Маргарита", "quantity": 25},
            {"dish": "Цезарь", "quantity": 18},
        ])
