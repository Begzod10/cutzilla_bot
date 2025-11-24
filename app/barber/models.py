from sqlalchemy import Integer, String, ForeignKey, BigInteger, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
from typing import Optional
from datetime import datetime
from app.service.models import Service
from app.client.models import Client, ClientRequest
from app.user.models import User


class Barber(Base):
    __tablename__ = "barbers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    login: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    img: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    midnight_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user = relationship("app.user.models.User", back_populates="barber", lazy="selectin")
    services = relationship("BarberService", back_populates="barber", lazy="selectin")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resume: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    requests = relationship("ClientRequest", back_populates="barber", lazy="selectin")
    schedule = relationship("BarberSchedule", back_populates="barber", lazy="selectin")
    selected_service: Mapped[int] = mapped_column(BigInteger, nullable=True)
    working_days = relationship("BarberWorkingDays", back_populates="barber", lazy="selectin",
                                order_by="BarberWorkingDays.id")
    scores = relationship("BarberServiceScore", back_populates="barber", lazy="selectin")
    clients = relationship("ClientBarbers", back_populates="barber", lazy="selectin")
    selected_schedule_id: Mapped[int] = mapped_column(BigInteger, nullable=True)


class BarberService(Base):
    __tablename__ = "barber_services"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    barber = relationship("Barber", back_populates="services", lazy="selectin")
    scores = relationship("BarberServiceScore", back_populates="barber_service", lazy="selectin")
    requests_services = relationship("ClientRequestService", back_populates="barber_service", lazy="selectin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    service = relationship("Service", back_populates="barber_service", lazy="selectin")


class BarberServiceScore(Base):
    __tablename__ = "barber_service_scores"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    barber_service_id: Mapped[int] = mapped_column(ForeignKey("barber_services.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"))
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    client_request_id: Mapped[int] = mapped_column(ForeignKey("client_requests.id"))
    comment: Mapped[str] = mapped_column(String(255), nullable=True)
    client_request = relationship("ClientRequest", back_populates="scores", lazy="selectin")
    client = relationship("Client", back_populates="scores", lazy="selectin")
    barber_service = relationship("BarberService", back_populates="scores", lazy="selectin")
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"), nullable=True)
    barber = relationship("Barber", back_populates="scores", lazy="selectin")


class BarberSchedule(Base):
    __tablename__ = "barber_schedule"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    day: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"))
    n_clients: Mapped[int] = mapped_column(Integer, nullable=True)
    total_income: Mapped[BigInteger] = mapped_column(BigInteger, nullable=True)
    barber = relationship("Barber", back_populates="schedule", lazy="selectin")
    details = relationship("BarberScheduleDetail", back_populates="barber_schedule", lazy="selectin")
    requests = relationship("ClientRequest", back_populates="barber_schedule", lazy="selectin")
    name_uz: Mapped[str] = mapped_column(String(50), nullable=True)
    name_ru: Mapped[str] = mapped_column(String(50), nullable=True)


class BarberScheduleDetail(Base):
    __tablename__ = "barber_schedule_details"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    barber_schedule_id: Mapped[int] = mapped_column(ForeignKey("barber_schedule.id"))
    from_time: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    to_time: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    client_request_id: Mapped[int] = mapped_column(ForeignKey("client_requests.id"))
    barber_schedule = relationship("BarberSchedule", back_populates="details", lazy="selectin")
    client_request = relationship("ClientRequest", back_populates="schedule_details", lazy="selectin")


class BarberWorkingDays(Base):
    __tablename__ = "barber_working_days"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"))
    name_uz: Mapped[str] = mapped_column(String(50), nullable=True)
    name_ru: Mapped[str] = mapped_column(String(50), nullable=True)
    barber = relationship("Barber", back_populates="working_days", lazy="selectin")
    is_working: Mapped[bool] = mapped_column(default=False)
