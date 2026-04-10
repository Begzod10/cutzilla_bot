from django.urls import path, include

urlpatterns = [
    path('service/', include('api.v1.service.urls')),
    path('auth/', include('api.v1.auth.urls')),
    path('region/', include('api.v1.region.urls')),
    path('user/', include('api.v1.user.urls')),
    path('client/', include('api.v1.client.urls')),
]
