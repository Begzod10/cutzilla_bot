from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from apps.service.models import Service
from .serializers import ServiceSerializer


class ServiceListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer


class ServiceDetailAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]  # Add this if needed for authentication
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    lookup_field = 'id'  # Ensure your URL pattern uses `id` as the parameter
