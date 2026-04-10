from django.urls import path
from .views import ServiceListAPIView, ServiceDetailAPIView

urlpatterns = [
    path('services/', ServiceListAPIView.as_view(), name='service-list'),
    path('services/<int:id>/', ServiceDetailAPIView.as_view(), name='service-detail'),
]
