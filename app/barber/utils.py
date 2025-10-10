from sqlalchemy import select, func
from app.barber.models import BarberWorkingDays, Barber, BarberService, BarberSchedule
from datetime import date
from app.user.models import User
from typing import List, Optional, Tuple
from datetime import datetime, time, timedelta
from app.client.models import Client, ClientRequest, ClientRequestService
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, cast, Date, and_, or_, distinct


PAGE_SIZE = 6
WEEKDAYS = {
    "uz": {
        1: "Dushanba",
        2: "Seshanba",
        3: "Chorshanba",
        4: "Payshanba",
        5: "Juma",
        6: "Shanba",
        7: "Yakshanba",
    },
    "ru": {
        1: "Понедельник",
        2: "Вторник",
        3: "Среда",
        4: "Четверг",
        5: "Пятница",
        6: "Суббота",
        7: "Воскресенье",
    },
}


async def seed_weekdays(session, barber_id: int):
    """Create weekdays for a barber if not already created (async)."""
    # ✅ Check if already seeded
    result = await session.execute(
        select(func.count()).select_from(BarberWorkingDays).where(
            BarberWorkingDays.barber_id == barber_id
        )
    )
    existing = result.scalar_one()

    if existing > 0:
        return  # prevent recreating

    # ✅ Insert weekdays
    for i in range(1, 8):
        weekday = BarberWorkingDays(
            barber_id=barber_id,
            name_uz=WEEKDAYS["uz"][i],
            name_ru=WEEKDAYS["ru"][i],
        )
        session.add(weekday)

    await session.commit()


WEEKDAY_UZ = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
WEEKDAY_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _is_ru(lang: str) -> bool:
    return (lang or "").lower().startswith("ru")


def _wd_names(lang: str) -> List[str]:
    return WEEKDAY_RU if _is_ru(lang) else WEEKDAY_UZ


def _t(lang: str, uz: str, ru: str) -> str:
    return ru if _is_ru(lang) else uz


def _fmt_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return "—"
    return dt.strftime("%H:%M")


def _fmt_d(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def week_bounds(today: date) -> Tuple[date, date]:
    monday = today - timedelta(days=today.weekday())  # Monday
    sunday = monday + timedelta(days=6)  # Sunday
    return monday, sunday


async def get_user_and_barber(session, telegram_id: int) -> Tuple[Optional["User"], Optional["Barber"], str]:
    user = (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if not user:
        return None, None, "uz"
    lang = getattr(user, "lang", "uz") or "uz"

    barber = (
        await session.execute(
            select(Barber).where(
                Barber.user_id == user.id,
                Barber.login == user.platform_login
            )
        )
    ).scalar_one_or_none()

    return user, barber, lang



