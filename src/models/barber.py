from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey, Time, Date, Text, Float
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class Barber(BaseModel):
    __tablename__ = "barbers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    per_hour = Column(Integer, default=0)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    score = Column(Integer, nullable=True)
    working_days = Column(Integer, default=0, nullable=True)
    img = Column(String, nullable=True)
    midnight_price = Column(Integer, default=0)

    login = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    resume = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_title = Column(String(255), nullable=True)
    selected_service = Column(BigInteger, nullable=True)
    selected_schedule_id = Column(BigInteger, nullable=True)

    user = relationship("User", back_populates="barber")
    barber_services = relationship("BarberService", back_populates="barber")
    client_requests = relationship("ClientRequest", back_populates="barber", foreign_keys="[ClientRequest.barber_id]")

    def __str__(self):
        return f"{self.user.name if self.user else self.id}"


class BarberService(BaseModel):
    __tablename__ = "barber_services"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(BigInteger, unique=True, index=True, nullable=True)
    barber_id = Column(Integer, ForeignKey("barbers.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    price = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)

    barber = relationship("Barber", back_populates="barber_services")
    service = relationship("Service", back_populates="barber_services")
    request_items = relationship("ClientRequestService", back_populates="barber_service")


class BarberSchedule(BaseModel):
    __tablename__ = "barber_schedule"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(BigInteger, unique=True, index=True, nullable=True)
    day = Column(Date, nullable=False)
    barber_id = Column(Integer, ForeignKey("barbers.id", ondelete="CASCADE"), nullable=False)
    n_clients = Column(Integer, default=0)
    total_income = Column(Integer, default=0)
    name_uz = Column(String(50), nullable=True)
    name_ru = Column(String(50), nullable=True)
    
    requests = relationship("ClientRequest", back_populates="barber_schedule", foreign_keys="[ClientRequest.barber_schedule_id]")


class BarberScheduleDetail(BaseModel):
    __tablename__ = "barber_schedule_details"

    id = Column(Integer, primary_key=True, index=True)
    barber_schedule_id = Column(Integer, ForeignKey("barber_schedule.id", ondelete="CASCADE"), nullable=False)
    from_time = Column(Time, nullable=False)
    to_time = Column(Time, nullable=False)
    status = Column(Boolean, default=False)
    client_request_id = Column(Integer, ForeignKey("client_requests.id", ondelete="CASCADE"), nullable=False)


class BarberServiceScore(BaseModel):
    __tablename__ = "barber_service_scores"

    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, ForeignKey("barbers.id", ondelete="CASCADE"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=True)
    barber_service_id = Column(Integer, ForeignKey("barber_services.id", ondelete="CASCADE"), nullable=True)
    comment = Column(Text, nullable=False)
    client_id = Column(Integer, ForeignKey("client.id", ondelete="CASCADE"), nullable=False)
    client_request_id = Column(Integer, ForeignKey("client_requests.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, default=0)


class BarberWorkingDays(BaseModel):
    __tablename__ = "barber_working_days"
    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, ForeignKey("barbers.id", ondelete="CASCADE"), nullable=False)
    name_uz = Column(String(50), nullable=True)
    name_ru = Column(String(50), nullable=True)
    is_working = Column(Boolean, default=False)
