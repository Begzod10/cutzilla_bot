from pydantic import BaseModel, ConfigDict
from typing import Optional

class ServiceBase(BaseModel):
    name_uz: Optional[str] = None
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    description_uz: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    disabled: Optional[bool] = False

class ServiceCreate(ServiceBase):
    pass

class ServiceResponse(ServiceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
