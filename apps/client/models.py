from django.db import models
from apps.common.models import BaseModel
from apps.users.models import Users

from apps.service.models import Service


class Client(BaseModel):
    external_id = models.BigIntegerField(unique=True, db_index=True, null=True)  # SA client.id
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="client")
    score = models.IntegerField(null=True, blank=True)
    blocked = models.BooleanField(default=False)


    # extras from SA Client
    selected_barber = models.ForeignKey(
        "barber.Barber", on_delete=models.SET_NULL, null=True, blank=True, related_name="selected_by_clients"
    )
    selected_schedule_id = models.BigIntegerField(null=True, blank=True)
    selected_request_id = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user}"


class ClientRequest(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accept", "Accept"),
        ("deny", "Deny"),
        ("done", "Done"),
        ("cancel", "Cancel"),
    ]

    external_id = models.BigIntegerField(unique=True, db_index=True, null=True)  # SA client_requests.id
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="requests")
    barber = models.ForeignKey("barber.Barber", on_delete=models.CASCADE, related_name="client_requests")
    date = models.DateField(null=True, blank=True)
    from_time = models.TimeField(null=True, blank=True)
    to_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    comment = models.TextField(null=True, blank=True)

    # extras from SA ClientRequest
    barber_schedule = models.ForeignKey("barber.BarberSchedule", on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name="requests")
    overall_score = models.IntegerField(null=True, blank=True)
    discount = models.IntegerField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)


class ClientRequestService(BaseModel):
    external_id = models.BigIntegerField(unique=True, db_index=True, null=True)  # SA client_requests_services.id
    client_request = models.ForeignKey(ClientRequest, on_delete=models.CASCADE, related_name="services")
    barber_service = models.ForeignKey("barber.BarberService", on_delete=models.CASCADE, related_name="request_items")
    duration = models.IntegerField(null=True, blank=True)
    status = models.BooleanField(default=False)


class ClientFavouriteBarbers(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    barber = models.ForeignKey("barber.Barber", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("client", "barber")
