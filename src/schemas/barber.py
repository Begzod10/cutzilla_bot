from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import time, date

class BarberBase(BaseModel):
    per_hour: Optional[int] = 0
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    working_days: Optional[int] = 0
    midnight_price: Optional[int] = 0

class BarberCreate(BarberBase):
    user_id: int

class BarberServiceItem(BaseModel):
    id: int
    barber_id: int
    service_id: int
    price: Optional[int] = None
    duration: Optional[int] = None

class BarberResponse(BarberBase):
    id: int
    user_id: int
    score: Optional[int] = None
    img: Optional[str] = None
    barber_services: Optional[List[BarberServiceItem]] = []

    model_config = ConfigDict(from_attributes=True)
