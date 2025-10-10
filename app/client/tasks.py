from app.celery_app import celery
from app.client.models import ClientRequest, ClientRequestService, Client
from app.barber.models import Barber, BarberService
import asyncio
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from sqlalchemy.orm import selectinload
from app.client.notification_utils import make_messages_ru_uz
from aiogram import Bot
import os
from sqlalchemy.sql.sqltypes import Date, Time
from sqlalchemy import select, and_, cast, or_
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.db import AsyncSessionLocal, async_engine
import requests
from typing import Any, Dict, List, Tuple
import logging
from asgiref.sync import async_to_sync

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TOKEN")

TZ = ZoneInfo("Asia/Tashkent")

log = logging.getLogger(__name__)

# ---- Django endpoint config (env-friendly, same pattern as your regions task)
API = os.getenv("API")
DJANGO_SYNC_TOKEN = os.getenv("DJANGO_LOCATION_TOKEN", "")
SYNC_CLIENT_URL = os.getenv("SYNC_CLIENT_URL")
SYNC_REQUEST_URL = os.getenv("SYNC_REQUEST_URL")
SYNC_REQ_SVC_URL = os.getenv("SYNC_REQ_SVC_URL")


def _to_naive_local(dt: datetime) -> datetime:
    """Convert any dt to Asia/Tashkent and drop tzinfo (for TIMESTAMP WITHOUT TIME ZONE columns)."""
    if dt.tzinfo is None:
        # assume the naive input is already local; keep it naive
        return dt
    return dt.astimezone(TZ).replace(tzinfo=None)


@celery.task(name="app.client.tasks.notify_upcoming_requests")
def notify_upcoming_requests():
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_notify_upcoming_requests_async())
        # ✅ dispose the real engine instance before closing the loop
        loop.run_until_complete(async_engine.dispose())
    finally:
        loop.close()


def _naive_local_now():
    now_local = datetime.now(TZ)  # aware
    return now_local, now_local.replace(tzinfo=None)  # aware, naive


async def _notify_upcoming_requests_async():
    now_local_aware, _ = _naive_local_now()

    # 1) today's business date (Asia/Tashkent)
    today_local_date = now_local_aware.date()  # date object (no tz)

    # 2) time-of-day window (HH:MM) ignoring date
    now_t = now_local_aware.time().replace(second=0, microsecond=0)
    soon_aware = now_local_aware + timedelta(hours=2)
    # Clamp to today's end (no next-day spill)
    end_t = soon_aware.time().replace(second=0, microsecond=0)
    if end_t <= now_t:
        # wrapping over midnight: clamp to 23:59:59 for "today only"
        end_t = time(23, 59, 59)
    async with AsyncSessionLocal() as session:
        q = (
            select(ClientRequest)
            .options(
                selectinload(ClientRequest.client).selectinload(Client.user),
                selectinload(ClientRequest.barber).selectinload(Barber.user),
                selectinload(ClientRequest.services)
                .selectinload(ClientRequestService.barber_service)
                .selectinload(BarberService.service),
            )
            .where(
                and_(
                    ClientRequest.status == "accept",
                    ClientRequest.from_time.is_not(None),

                    # A) match *today* by business date
                    cast(ClientRequest.date, Date) == today_local_date,

                    # B) time-of-day window (ignore date on from_time)
                    cast(ClientRequest.from_time, Time) >= now_t,
                    cast(ClientRequest.from_time, Time) < end_t,

                    ClientRequest.reminder_sent_at.is_(None),
                )
            )
            .order_by(ClientRequest.from_time.asc())
        )

        result = await session.execute(q)
        requests = result.scalars().all()
        if not requests:
            return

        bot = Bot(
            token=TELEGRAM_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        try:
            for cr in requests:
                # Build localized messages (utils internally formats with TZ for display)
                msg_for_client, msg_for_barber = make_messages_ru_uz(cr, TZ)

                client_tg = getattr(getattr(cr.client, "user", None), "telegram_id", None)
                barber_tg = getattr(getattr(cr.barber, "user", None), "telegram_id", None)

                if client_tg:
                    try:
                        await bot.send_message(client_tg, msg_for_client)
                    except Exception:
                        pass
                if barber_tg:
                    try:
                        await bot.send_message(barber_tg, msg_for_barber)
                    except Exception:
                        pass

                # ⬇️ write NAIVE timestamp back to DB column (reminder_sent_at is WITHOUT TZ)
                cr.reminder_sent_at = _naive_local_now()[1]
            await session.commit()
        finally:
            await bot.session.close()
