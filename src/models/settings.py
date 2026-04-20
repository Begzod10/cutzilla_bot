from sqlalchemy import Column, String, Text
from src.models.base import BaseModel

class SystemSetting(BaseModel):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    def __str__(self):
        return f"{self.key}: {self.value}"
