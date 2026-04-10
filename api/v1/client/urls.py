# app: client/api/urls.py
from django.urls import path
from .views import SyncUserView

urlpatterns = [
    path("add/", SyncUserView.as_view(), name="sync-client"),

]
