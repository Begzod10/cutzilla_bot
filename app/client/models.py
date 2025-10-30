from app.db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import datetime
from sqlalchemy import DateTime


class Client(Base):
    __tablename__ = "client"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=True)
    requests = relationship("ClientRequest", back_populates="client", lazy="selectin")
    scores = relationship("BarberServiceScore", back_populates="client", lazy="selectin")
    user = relationship("app.user.models.User", back_populates="client", uselist=False, lazy="selectin")
    selected_barber: Mapped[int] = mapped_column(BigInteger, nullable=True)
    selected_schedule_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    selected_request_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    barbers = relationship("ClientBarbers", back_populates="client", lazy="selectin")


class ClientRequest(Base):
    __tablename__ = "client_requests"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"))
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"))
    date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    from_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    to_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    client = relationship("Client", back_populates="requests")
    barber = relationship("Barber", back_populates="requests")
    status: Mapped[str] = mapped_column(String(255), nullable=True, default="pending")
    comment: Mapped[str] = mapped_column(String(255), nullable=True)
    scores = relationship("BarberServiceScore", back_populates="client_request", lazy="selectin")
    schedule_details = relationship("BarberScheduleDetail", back_populates="client_request", lazy="selectin")
    services = relationship("ClientRequestService", back_populates="client_request", lazy="selectin")
    barber_schedule_id: Mapped[int] = mapped_column(ForeignKey("barber_schedule.id", ondelete="CASCADE"), nullable=True)
    barber_schedule = relationship("BarberSchedule", back_populates="requests", lazy="selectin")
    overall_score: Mapped[int] = mapped_column(Integer, nullable=True)
    discount: Mapped[int] = mapped_column(Integer, nullable=True)
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ClientRequestService(Base):
    __tablename__ = "client_requests_services"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_request_id: Mapped[int] = mapped_column(ForeignKey("client_requests.id"))
    barber_service_id: Mapped[int] = mapped_column(ForeignKey("barber_services.id"))
    barber_service = relationship("BarberService", back_populates="requests_services")
    duration: Mapped[int] = mapped_column(Integer, nullable=True)
    client_request = relationship("ClientRequest", back_populates="services")
    status: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)


class ClientBarbers(Base):
    __tablename__ = "client_barbers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"))
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"))
    client = relationship("Client", back_populates="barbers")
    barber = relationship("Barber", back_populates="clients")
