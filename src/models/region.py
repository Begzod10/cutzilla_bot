from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Country(Base):
    __tablename__ = "country"

    id = Column(Integer, primary_key=True, index=True)
    name_uz = Column(String(100), nullable=True)
    name_ru = Column(String(100), nullable=True)
    name_en = Column(String(100), nullable=True)

    regions = relationship("Region", back_populates="country")
    cities = relationship("City", back_populates="country")


class Region(Base):
    __tablename__ = "region"

    id = Column(Integer, primary_key=True, index=True)
    name_uz = Column(String(100), nullable=True)
    name_ru = Column(String(100), nullable=True)
    name_en = Column(String(100), nullable=True)
    country_id = Column(Integer, ForeignKey("country.id", ondelete="CASCADE"), nullable=False)

    country = relationship("Country", back_populates="regions")
    cities = relationship("City", back_populates="region")


class City(Base):
    __tablename__ = "city"

    id = Column(Integer, primary_key=True, index=True)
    name_uz = Column(String(100), nullable=True)
    name_ru = Column(String(100), nullable=True)
    name_en = Column(String(100), nullable=True)
    country_id = Column(Integer, ForeignKey("country.id", ondelete="CASCADE"), nullable=True)
    region_id = Column(Integer, ForeignKey("region.id", ondelete="CASCADE"), nullable=False)

    country = relationship("Country", back_populates="cities")
    region = relationship("Region", back_populates="cities")
