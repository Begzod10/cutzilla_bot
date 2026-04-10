from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey, Time, Date, Text, DateTime
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class Client(BaseModel):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(BigInteger, unique=True, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=True)
    blocked = Column(Boolean, default=False)

    selected_barber_id = Column(Integer, ForeignKey("barbers.id", ondelete="SET NULL"), nullable=True)
    selected_barber = Column(BigInteger, nullable=True)
    selected_schedule_id = Column(BigInteger, nullable=True)
    selected_request_id = Column(BigInteger, nullable=True)

    user = relationship("User", back_populates="client")
    requests = relationship("ClientRequest", back_populates="client", foreign_keys="[ClientRequest.client_id]")


class ClientRequest(BaseModel):
    __tablename__ = "client_requests"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(BigInteger, unique=True, index=True, nullable=True)
    client_id = Column(Integer, ForeignKey("client.id", ondelete="CASCADE"), nullable=False)
    barber_id = Column(Integer, ForeignKey("barbers.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=True)
    from_time = Column(Time, nullable=True)
    to_time = Column(Time, nullable=True)
    status = Column(String(20), default="pending")
    comment = Column(Text, nullable=True)

    barber_schedule_id = Column(Integer, ForeignKey("barber_schedule.id", ondelete="SET NULL"), nullable=True)
    overall_score = Column(Integer, nullable=True)
    discount = Column(Integer, nullable=True)
    reminder_sent_at = Column(DateTime, nullable=True)

    client = relationship("Client", back_populates="requests", foreign_keys=[client_id])
    barber = relationship("Barber", back_populates="client_requests", foreign_keys=[barber_id])
    barber_schedule = relationship("BarberSchedule", back_populates="requests", foreign_keys=[barber_schedule_id])
    services = relationship("ClientRequestService", back_populates="client_request")


class ClientRequestService(BaseModel):
    __tablename__ = "client_requests_services"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(BigInteger, unique=True, index=True, nullable=True)
    client_request_id = Column(Integer, ForeignKey("client_requests.id", ondelete="CASCADE"), nullable=False)
    barber_service_id = Column(Integer, ForeignKey("barber_services.id", ondelete="CASCADE"), nullable=False)
    duration = Column(Integer, nullable=True)
    status = Column(Boolean, default=False)

    client_request = relationship("ClientRequest", back_populates="services")
    barber_service = relationship("BarberService", back_populates="request_items")


class ClientFavouriteBarbers(BaseModel):
    __tablename__ = "client_barbers"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client.id", ondelete="CASCADE"), nullable=False)
    barber_id = Column(Integer, ForeignKey("barbers.id", ondelete="CASCADE"), nullable=False)
