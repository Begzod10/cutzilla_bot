from sqlalchemy import Integer, String, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from sqlalchemy import Table, Column, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional
from sqlalchemy.ext.declarative import declarative_base


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=True)
    surname: Mapped[str] = mapped_column(String(50), nullable=True)
    telegram_id = Column(BigInteger, unique=True)
    platform_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    platform_login: Mapped[str] = mapped_column(String(50), nullable=True)
    user_type: Mapped[str] = mapped_column(String(50), nullable=True)
    lang: Mapped[str] = mapped_column(String(2), nullable=True)

    barber = relationship("Barber", back_populates="user", uselist=False)
    client = relationship("Client", back_populates="user", uselist=False)

    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"), nullable=True)
    country = relationship("Country", back_populates="users")

    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"), nullable=True)
    region = relationship("Region", back_populates="users")

    city_id: Mapped[int] = mapped_column(ForeignKey("city.id"), nullable=True)
    city = relationship("City", back_populates="users")

