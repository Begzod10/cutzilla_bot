from rest_framework import serializers
from apps.service.models import Service, ServiceImage


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ['id', 'image']


class ServiceSerializer(serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id',
            'name_uz', 'name_ru', 'name_en',
            'description_uz', 'description_ru', 'description_en',
            'images', "disabled"
        ]
