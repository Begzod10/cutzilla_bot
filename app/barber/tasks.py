import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery
from app.barber.models import Barber, BarberSchedule
from app.db import AsyncSessionLocal  # ✅ make sure this points to your async session factory
from celery import shared_task
import os
from typing import List, Dict, Any
import requests

# Uzbek and Russian weekday names
WEEKDAY_NAMES_UZ = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
WEEKDAY_NAMES_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
API = os.getenv("API", "http://127.0.0.1:8000").rstrip("/")
LOCATION_PUSH_URL = os.getenv("LOCATION_PUSH_URL").lstrip("/")
DJANGO_LOCATION_TOKEN = os.getenv("DJANGO_LOCATION_TOKEN", "")


@celery.task(name='app.tasks.create_barber_schedule', ignore_result=True)
def create_barber_schedule():
    """Celery entrypoint — keep it sync; run the async job on a fresh loop."""
    asyncio.run(_create_barber_schedule())


async def _create_barber_schedule():
    today = datetime.now().date()
    days_ahead = 40

    # open session explicitly so we can close & dispose before leaving the loop
    session = AsyncSessionLocal()
    engine = session.bind  # AsyncEngine

    try:
        async with session:
            # Get all barbers
            result = await session.execute(select(Barber))
            barbers = result.scalars().all()

            for barber in barbers:
                for offset in range(days_ahead):
                    schedule_date = today + timedelta(days=offset)
                    weekday_index = schedule_date.weekday()  # 0=Mon..6=Sun

                    # Prevent duplicates
                    exists = (
                        await session.execute(
                            select(BarberSchedule.id).where(
                                BarberSchedule.barber_id == barber.id,
                                BarberSchedule.day == schedule_date,
                            )
                        )
                    ).scalar_one_or_none()
                    if exists:
                        continue

                    session.add(
                        BarberSchedule(
                            barber_id=barber.id,
                            day=schedule_date,
                            name_uz=WEEKDAY_NAMES_UZ[weekday_index],
                            name_ru=WEEKDAY_NAMES_RU[weekday_index],
                        )
                    )

            await session.commit()

    except Exception:
        # rollback while loop is alive so asyncpg can do its thing
        try:
            await session.rollback()
        finally:
            # re-raise so Celery backoff/etc. still works (optional)
            raise
    finally:
        # 1) close the session inside the running loop
        try:
            await session.close()
        finally:
            # 2) dispose the engine (drops pooled conns) before loop ends
            if engine is not None:
                try:
                    await engine.dispose()
                except Exception:
                    # swallow dispose errors to avoid masking the original
                    pass


def _headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if DJANGO_LOCATION_TOKEN:
        h["Authorization"] = f"Token {DJANGO_LOCATION_TOKEN}"
    return h


@shared_task(name="sync_locations_to_django", bind=False, autoretry_for=(Exception,), retry_backoff=5,
             retry_kwargs={"max_retries": 5})
def sync_locations_to_django(items: List[Dict[str, Any]]) -> None:
    """
    items: list of dicts with keys:
      country_uz, country_ru, country_en (optional)
      region_uz, region_ru, region_en (optional)
      city_uz,   city_ru,   city_en   (optional)
    """
    url = f"{API}/{LOCATION_PUSH_URL}"
    r = requests.post(url, json=items, headers=_headers(), timeout=30)
    # log non-200s; don't raise to avoid celery hard-fail storms
    if r.status_code != 200:
        try:
            body = r.text[:500]
        except Exception:
            body = "<no body>"
        print(f"[sync_locations_to_django] POST {url} -> {r.status_code} {body}")
