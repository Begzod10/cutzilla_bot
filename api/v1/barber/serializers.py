from rest_framework import serializers
from apps.barber.models import Barber, BarberService


class BarberServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarberService
        fields = '__all__'


class BarberSerializer(serializers.ModelSerializer):
    barber_services = serializers.SerializerMethodField()

    class Meta:
        model = Barber
        fields = ['per_hour', 'start_time', 'end_time', 'score', 'working_days', 'img', 'midnight_price',
                  'barber_services']

    def get_barber_services(self, obj):
        barber_services = BarberService.objects.filter(barber=obj)
        return BarberServiceSerializer(barber_services, many=True).data
