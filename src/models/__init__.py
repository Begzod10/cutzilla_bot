from src.models.base import BaseModel
from src.models.users import User
from src.models.barber import Barber, BarberService, BarberSchedule, BarberScheduleDetail, BarberServiceScore
from src.models.client import Client, ClientRequest, ClientRequestService, ClientFavouriteBarbers
from src.models.service import Service, ServiceImage
from src.models.region import Country, Region, City

# This guarantees all models are loaded before Alembic metadata is grabbed
