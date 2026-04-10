from django.db import models
from apps.users.models import Users
from apps.client.models import Client
from apps.common.models import BaseModel
from apps.service.models import Service


# Create your models here.
class Barber(BaseModel):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    per_hour = models.IntegerField(default=0)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    working_days = models.IntegerField(default=0, null=True, blank=True)
    img = models.ImageField(upload_to='barber/', null=True, blank=True)
    midnight_price = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


class BarberService(BaseModel):
    external_id = models.BigIntegerField(unique=True, db_index=True, null=True, blank=True)
    barber = models.ForeignKey("barber.Barber", on_delete=models.CASCADE, related_name="barber_services")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="barber_services")
    price = models.IntegerField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # minutes


class BarberSchedule(BaseModel):
    external_id = models.BigIntegerField(unique=True, db_index=True, null=True, blank=True)
    day = models.DateField()
    barber = models.ForeignKey(Barber, on_delete=models.CASCADE)
    n_clients = models.IntegerField(default=0)
    total_income = models.IntegerField(default=0)


class BarberScheduleDetail(BaseModel):
    barber_schedule = models.ForeignKey(BarberSchedule, on_delete=models.CASCADE)
    from_time = models.TimeField()
    to_time = models.TimeField()
    status = models.BooleanField(default=False)
    client_request = models.ForeignKey('client.ClientRequest', on_delete=models.CASCADE)


class BarberServiceScore(BaseModel):
    barber = models.ForeignKey(Barber, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    comment = models.TextField()
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    client_request = models.ForeignKey('client.ClientRequest', on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

