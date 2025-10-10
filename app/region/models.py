from app.db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional


class Country(Base):
    __tablename__ = "country"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name_uz: Mapped[str] = mapped_column(String(50), nullable=True)
    name_ru: Mapped[str] = mapped_column(String(50), nullable=True)
    name_en: Mapped[str] = mapped_column(String(50), nullable=True)
    regions = relationship("Region", back_populates="country")
    users = relationship("User", back_populates="country")


class Region(Base):
    __tablename__ = "region"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name_uz: Mapped[str] = mapped_column(String(50), nullable=True)
    name_ru: Mapped[str] = mapped_column(String(50), nullable=True)
    name_en: Mapped[str] = mapped_column(String(50), nullable=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"))
    country = relationship("Country", back_populates="regions")
    cities = relationship("City", back_populates="region")
    users = relationship("User", back_populates="region")


class City(Base):
    __tablename__ = "city"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name_uz: Mapped[str] = mapped_column(String(50), nullable=True)
    name_ru: Mapped[str] = mapped_column(String(50), nullable=True)
    name_en: Mapped[str] = mapped_column(String(50), nullable=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"))
    region = relationship("Region", back_populates="cities")
    users = relationship("User", back_populates="city")
