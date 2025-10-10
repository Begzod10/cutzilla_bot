from sqlalchemy import Integer, String, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from sqlalchemy import Table, Column, ForeignKey, BigInteger, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional
from sqlalchemy.ext.declarative import declarative_base


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name_uz: Mapped[str] = mapped_column(String(50), nullable=True)
    name_ru: Mapped[str] = mapped_column(String(50), nullable=True)
    name_en: Mapped[str] = mapped_column(String(50), nullable=True)
    description_uz: Mapped[str] = mapped_column(String(255), nullable=True)
    description_ru: Mapped[str] = mapped_column(String(255), nullable=True)
    description_en: Mapped[str] = mapped_column(String(255), nullable=True)
    platform_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    # DO NOT define barbers here yet
    images = relationship("ServiceImages", backref="service", cascade="all, delete-orphan")
    barber_service = relationship("BarberService", back_populates="service", lazy="selectin")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)


class ServiceImages(Base):
    __tablename__ = "service_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
