from rest_framework import serializers
from apps.region.models import Region, Country, City


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = "__all__"


class RegionSerializer(serializers.ModelSerializer):
    cities = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ["id", "name_uz", "name_ru", "name_en", "cities"]

    def get_cities(self, obj):
        return CitySerializer(obj.city_set.all(), many=True).data


class CountrySerializer(serializers.ModelSerializer):
    regions = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ["id", "name_uz", "name_ru", "name_en", "regions"]

    def get_regions(self, obj):
        return RegionSerializer(obj.region_set.all(), many=True).data
