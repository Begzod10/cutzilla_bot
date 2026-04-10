from django.urls import path
from .views import CountryListView, LocationData, LocationPushView

urlpatterns = [
    path('countries/', CountryListView.as_view(), name='country-list'),
    path("locations/push/", LocationPushView.as_view(), name="location-push"),
]
