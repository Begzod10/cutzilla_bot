from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.barber.models import Barber, BarberWorkingDays
from app.user.models import User
from .keyboards import barber_working_days_keyboard
from app.db import AsyncSessionLocal
from .utils import seed_weekdays

barber_working_days_route = Router()


@barber_working_days_route.message(F.text.in_({"📅 Ish kunlari", "📅 Рабочие дни"}))
async def barber_working_days(message: Message, state: FSMContext):
    tg_user = message.from_user

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == tg_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await message.answer("❌ User not found.")
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            text = "Sartarosh topilmadi." if user.lang == "uz" else "Барбер не найден."
            await message.answer(text)
            return

        # ✅ Seed weekdays if not already created
        await seed_weekdays(session, barber.id)

        # ✅ Fetch weekdays
        days = (
            await session.execute(
                select(BarberWorkingDays).where(BarberWorkingDays.barber_id == barber.id)
            )
        ).scalars().all()

        text = "📅 Ish kunlarini tanlang:" if user.lang == "uz" else "📅 Выберите рабочие дни:"
        await message.answer(text, reply_markup=barber_working_days_keyboard(days, user.lang))


@barber_working_days_route.callback_query(F.data.startswith("toggle_day:"))
async def toggle_working_day(callback: CallbackQuery):
    day_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        day = (
            await session.execute(
                select(BarberWorkingDays).where(BarberWorkingDays.id == day_id)
            )
        ).scalar_one_or_none()

        if not day:
            await callback.answer("Xato!" if callback.from_user.language_code == "uz" else "Ошибка!", show_alert=True)
            return

        # ✅ Toggle status
        day.is_working = not day.is_working
        await session.commit()

        # ✅ Reload days for keyboard
        days = (
            await session.execute(
                select(BarberWorkingDays)
                .where(BarberWorkingDays.barber_id == day.barber_id)
                .order_by(BarberWorkingDays.id)
            )
        ).scalars().all()
        lang = user.lang if user else "uz"

        await callback.message.edit_reply_markup(
            reply_markup=barber_working_days_keyboard(days, lang)
        )

    await callback.answer("Yangilandi ✅" if lang == "uz" else "Обновлено ✅")
