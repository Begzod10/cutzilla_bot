from datetime import datetime
import asyncio
from typing import Optional, Tuple
import httpx
from geopy.geocoders import Nominatim
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os

from app.region.models import Country, Region, City

load_dotenv()
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
BASE_URL = "https://geocode-maps.yandex.ru/1.x"


# ------------------ HELPERS ------------------

def _norm(s: Optional[str]) -> Optional[str]:
    return s.strip() if s and s.strip() else None


async def get_location_yandex(lat: float, lon: float, lang: str = "uz_UZ") -> dict:
    if not YANDEX_API_KEY:
        return {"country": None, "region": None, "city": None}

    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": f"{lon},{lat}",  # Yandex expects lon,lat
        "format": "json",
        "lang": lang,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    try:
        comps = (
            data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
            ["metaDataProperty"]["GeocoderMetaData"]["Address"]["Components"]
        )
        parts = {c["kind"]: c["name"] for c in comps if isinstance(c, dict)}
        return {
            "country": parts.get("country"),
            "region": parts.get("province") or parts.get("area"),
            "city": parts.get("locality") or parts.get("area"),
        }
    except (KeyError, IndexError, TypeError):
        return {"country": None, "region": None, "city": None}


async def get_location_nominatim(lat: float, lon: float, lang: str = "uz") -> dict:
    geolocator = Nominatim(user_agent="location_bot")

    def _reverse():
        loc = geolocator.reverse((lat, lon), language=lang)
        if loc and "address" in getattr(loc, "raw", {}):
            addr = loc.raw["address"]
            return {
                "city": addr.get("city") or addr.get("town") or addr.get("village"),
                "region": addr.get("state"),
                "country": addr.get("country"),
            }
        return {"city": None, "region": None, "country": None}

    return await asyncio.to_thread(_reverse)


async def _get_or_create_country(session: AsyncSession, name_uz: str, name_ru: str) -> Country:
    q = select(Country).where(Country.name_uz == name_uz)
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing:
        if not existing.name_ru and name_ru:
            existing.name_ru = name_ru
        return existing
    obj = Country(name_uz=name_uz, name_ru=name_ru)
    session.add(obj)
    await session.flush()
    return obj


async def _get_or_create_region(session: AsyncSession, country_id: int, name_uz: str, name_ru: str) -> Region:
    q = select(Region).where(Region.country_id == country_id, Region.name_uz == name_uz)
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing:
        if not existing.name_ru and name_ru:
            existing.name_ru = name_ru
        return existing
    obj = Region(name_uz=name_uz, name_ru=name_ru, country_id=country_id)
    session.add(obj)
    await session.flush()
    return obj


async def _get_or_create_city(session: AsyncSession, region_id: int, name_uz: str, name_ru: str) -> City:
    q = select(City).where(City.region_id == region_id, City.name_uz == name_uz)
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing:
        if not existing.name_ru and name_ru:
            existing.name_ru = name_ru
        return existing
    obj = City(name_uz=name_uz, name_ru=name_ru, region_id=region_id)
    session.add(obj)
    await session.flush()
    return obj


# ------------------ MAIN FUNCTION ------------------

async def get_region_city_multilang(session: AsyncSession, lat: float, lon: float) -> Tuple[Country, Region, City]:
    """
    Try Yandex in UZ+RU; fallback to Nominatim if missing city/region.
    Then upsert Country, Region, City.
    """
    uz = await get_location_yandex(lat, lon, "uz_UZ")
    ru = await get_location_yandex(lat, lon, "ru_RU")

    # If Yandex failed to give city/region, fallback
    if not uz.get("city") or not uz.get("region"):
        uz = await get_location_nominatim(lat, lon, "uz")
    if not ru.get("city") or not ru.get("region"):
        ru = await get_location_nominatim(lat, lon, "ru")

    uz_country = _norm(uz.get("country")) or _norm(ru.get("country"))
    uz_region = _norm(uz.get("region")) or _norm(ru.get("region"))
    uz_city = _norm(uz.get("city")) or _norm(ru.get("city"))

    ru_country = _norm(ru.get("country")) or uz_country
    ru_region = _norm(ru.get("region")) or uz_region
    ru_city = _norm(ru.get("city")) or uz_city

    # Upsert into DB
    country = await _get_or_create_country(session, uz_country, ru_country)
    region = await _get_or_create_region(session, country.id, uz_region, ru_region)
    city = await _get_or_create_city(session, region.id, uz_city, ru_city)
    payload = [{
        "country_uz": country.name_uz,
        "country_ru": country.name_ru,
        "country_en": getattr(country, "name_en", None),

        "region_uz": region.name_uz,
        "region_ru": region.name_ru,
        "region_en": getattr(region, "name_en", None),

        "city_uz": city.name_uz,
        "city_ru": city.name_ru,
        "city_en": getattr(city, "name_en", None),
    }]
    from app.barber.tasks import sync_locations_to_django
    sync_locations_to_django.delay(payload)
    return country, region, city


# ------------------ FREE SLOTS ------------------

def find_free_slots(work_start: datetime, work_end: datetime, busy_times: list[tuple[datetime, datetime]],
                    duration_minutes: int):
    """
    Returns a list of available start times (as datetime objects).
    busy_times: list of tuples (from_time, to_time)
    """
    available_slots = []
    current = work_start

    # Sort busy intervals
    busy_times = sorted(busy_times, key=lambda x: x[0])

    for busy_start, busy_end in busy_times:
        # If gap between current and busy_start is enough
        if (busy_start - current).total_seconds() / 60 >= duration_minutes:
            available_slots.append(current)
        # Move current to after this busy slot
        if busy_end > current:
            current = busy_end

    # After last busy slot
    if (work_end - current).total_seconds() / 60 >= duration_minutes:
        available_slots.append(current)

    return available_slots
