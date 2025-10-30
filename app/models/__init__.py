# app/models/__init__.py
from app.db import Base  # same Base used everywhere

# ⚠️ ORDER MATTERS. Import geo first so Country/Region/City exist
import app.region.models  # Country, Region, City
import app.user.models  # User
import app.client.models  # Client
import app.barber.models  # Barber, BarberService, BarberSchedule, ClientRequest, ClientRequestService
import app.service.models  # Service, ServiceImage

# Now freeze/validate mappers only AFTER everything is imported
from sqlalchemy.orm import configure_mappers

configure_mappers()

from app.user.models import User
from app.barber.models import Barber, BarberSchedule, BarberService
from app.client.models import Client, ClientRequest
from app.service.models import Service

__all__ = ["User", "Barber", "BarberSchedule", "Client", "ClientRequest", "Service", "BarberService"]
