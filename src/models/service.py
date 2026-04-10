from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class Service(BaseModel):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name_uz = Column(String(255), nullable=True)
    name_ru = Column(String(255), nullable=True)
    name_en = Column(String(255), nullable=True)

    description_uz = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    platform_id = Column(BigInteger, nullable=True)
    
    disabled = Column(Boolean, default=False, nullable=True)

    barber_services = relationship("BarberService", back_populates="service")
    service_images = relationship("ServiceImage", back_populates="service")


class ServiceImage(BaseModel):
    __tablename__ = "service_images"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    image = Column(String, nullable=False)

    service = relationship("Service", back_populates="service_images")
