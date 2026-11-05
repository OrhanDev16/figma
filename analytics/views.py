from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class OverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"detail": "overview works"})


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"detail": "analytics works"})

