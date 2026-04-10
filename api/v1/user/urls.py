# api/v1/users/urls.py
from django.urls import path
from .views import SyncUserView

urlpatterns = [
    path("sync/user/", SyncUserView.as_view(), name="sync-user"),
]
