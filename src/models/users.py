from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Float
from src.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    password = Column(String(128), nullable=True)
    last_login = Column(String, nullable=True) # Usually datetime but storing it safely, or let's use DateTime
    is_superuser = Column(Boolean, default=False)
    username = Column(String(150), unique=True, index=True)
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    email = Column(String(254), nullable=True)
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    date_joined = Column(String, nullable=True) # Django date_joined
    
    role = Column(String(20), default='user')
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    referred_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    balance = Column(BigInteger, default=0) # In Som

    name = Column(String(150), nullable=True)
    surname = Column(String(150), nullable=True)
    platform_id = Column(BigInteger, nullable=True)
    platform_login = Column(String(50), nullable=True)
    user_type = Column(String(50), nullable=True)
    lang = Column(String(2), nullable=True)
    country_id = Column(Integer, ForeignKey("country.id", ondelete="SET NULL"), nullable=True)
    region_id = Column(Integer, ForeignKey("region.id", ondelete="SET NULL"), nullable=True)
    city_id = Column(Integer, ForeignKey("city.id", ondelete="SET NULL"), nullable=True)

    barber = relationship("Barber", back_populates="user", uselist=False)
    client = relationship("Client", back_populates="user", uselist=False)
    
    referred_by = relationship("User", remote_side=[id], backref="referrals")

    def __str__(self):
        return f"{self.name or self.username or self.id}"
