from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class RegionBase(BaseModel):
    name_uz: Optional[str] = None
    name_ru: Optional[str] = None
    name_en: Optional[str] = None

class RegionResponse(RegionBase):
    id: int
    country_id: int

    model_config = ConfigDict(from_attributes=True)

class CountryResponse(BaseModel):
    id: int
    name_uz: Optional[str] = None
    name_ru: Optional[str] = None
    name_en: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CityInput(BaseModel):
    name_uz: Optional[str] = None
    name_ru: Optional[str] = None
    name_en: Optional[str] = None

class RegionInput(BaseModel):
    name_uz: Optional[str] = None
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    cities: Optional[List[CityInput]] = []

class CountryInput(BaseModel):
    name_uz: Optional[str] = None
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    regions: Optional[List[RegionInput]] = []

class LocationDataPayload(BaseModel):
    countries: List[CountryInput]

class LocationPushPayload(BaseModel):
    country_uz: Optional[str] = None
    country_ru: Optional[str] = None
    country_en: Optional[str] = None
    region_uz: Optional[str] = None
    region_ru: Optional[str] = None
    region_en: Optional[str] = None
    city_uz: Optional[str] = None
    city_ru: Optional[str] = None
    city_en: Optional[str] = None
