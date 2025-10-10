from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.states import LoginState, ChangeLocation
from app.user.models import User
from app.barber.models import (
    Barber, BarberService, BarberSchedule, BarberScheduleDetail,
    ClientRequest, BarberWorkingDays
)
from app.service.models import Service
from app.client.models import Client
from .keyboards import (
    format_barber_schedule_days,
    kb_with_client_back, send_schedule_page,
    barber_list_keyboard, kb_day_slots_by_sched_client
)
from .utils import get_region_city_multilang
from app.region.models import Country, Region, City

# import your async session factory
from app.db import AsyncSessionLocal  # adjust path if needed
from app.client.models import ClientBarbers

barber_profile = Router()


@barber_profile.message(F.text.in_(["✂️ Sartarosh haqida", "✂️ Информация о барбере"]))
async def barber_profile_info(message: Message, state: FSMContext):
    tg_user = message.from_user

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == tg_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await message.answer(
                "❌ Пользователь не найден." if tg_user.language_code == "ru" else "❌ Foydalanuvchi topilmadi."
            )
            return

        client = (
            await session.execute(
                select(Client).where(Client.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not client or not client.selected_barber:
            text = "Barber tanlanmagan." if (user.lang or "uz") == "uz" else "Барбер не выбран."
            await message.answer(text)
            return

        barber = (
            await session.execute(
                select(Barber)
                .options(selectinload(Barber.user), selectinload(Barber.working_days))
                .where(Barber.id == client.selected_barber)
                .limit(1)
            )
        ).scalar_one_or_none()

        if not barber:
            text = "Barber topilmadi." if (user.lang or "uz") == "uz" else "Барбер не найден."
            await message.answer(text)
            return

        # 🔍 Check if already in client's list
        existing = (
            await session.execute(
                select(ClientBarbers).where(
                    ClientBarbers.client_id == client.id,
                    ClientBarbers.barber_id == barber.id
                )
            )
        ).scalar_one_or_none()

    kb = barber_list_keyboard(user.lang or "uz", barber.id, existing is not None)

    if (user.lang or "uz") == "uz":
        working_days = ", ".join(
            [day.name_uz for day in barber.working_days if getattr(day, "is_working", False)]) or "Nomaʼlum"
        text = (
            f"✂️ **Sartarosh maʼlumotlari**\n\n"
            f"👤 Ism: {barber.user.name if barber.user else ''}\n"
            f"👤 Familiya: {barber.user.surname if barber.user else ''}\n"
            f"⭐️ Reyting: {barber.score or 'Nomaʼlum'}\n"
            f"📅 Ish kunlari: {working_days}\n"
            f"🕒 Boshlanish vaqti: {barber.start_time.strftime('%H:%M') if barber.start_time else 'Nomaʼlum'}\n"
            f"🕒 Tugash vaqti: {barber.end_time.strftime('%H:%M') if barber.end_time else 'Nomaʼlum'}"
        )
    else:
        working_days = ", ".join(
            [day.name_ru for day in barber.working_days if getattr(day, "is_working", False)]) or "Неизвестно"
        text = (
            f"✂️ **Информация о барбере**\n\n"
            f"👤 Имя: {barber.user.name if barber.user else ''}\n"
            f"👤 Фамилия: {barber.user.surname if barber.user else ''}\n"
            f"⭐️ Рейтинг: {barber.score or 'Неизвестно'}\n"
            f"📅 Рабочие дни: {working_days}\n"
            f"🕒 Время начала: {barber.start_time.strftime('%H:%M') if barber.start_time else 'Неизвестно'}\n"
            f"🕒 Время окончания: {barber.end_time.strftime('%H:%M') if barber.end_time else 'Неизвестно'}"
        )

    lang = (user.lang or "uz")
    if barber and barber.latitude and barber.longitude:
        await message.answer_venue(
            latitude=barber.latitude,
            longitude=barber.longitude,
            title=barber.location_title or ("Мой салон" if lang == "ru" else "Mening salonim"),
            address=barber.address or ("Адрес не указан" if lang == "ru" else "Manzil kiritilmagan")
        )

    else:
        await message.answer(
            "❌ Локация не найдена" if lang == "ru" else "❌ Joylashuv topilmadi",
        )
    if barber.img and isinstance(barber.img, str):
        if barber.img.startswith("http"):
            await message.answer_photo(photo=barber.img, caption=text, reply_markup=kb)
        else:
            try:
                await message.answer_photo(photo=FSInputFile(barber.img), caption=text, reply_markup=kb)
            except Exception:
                await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@barber_profile.callback_query(F.data.startswith("addbarber:"))
async def add_barber_cb(call: CallbackQuery):
    barber_id = int(call.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == call.from_user.id))
        ).scalar_one_or_none()
        if not user:
            await call.answer("❌ User not found", show_alert=True)
            return

        client = (
            await session.execute(select(Client).where(Client.user_id == user.id))
        ).scalar_one_or_none()
        if not client:
            await call.answer("❌ Client not found", show_alert=True)
            return

        # prevent duplicates
        existing = (
            await session.execute(
                select(ClientBarbers).where(
                    ClientBarbers.client_id == client.id,
                    ClientBarbers.barber_id == barber_id
                )
            )
        ).scalar_one_or_none()
        if existing:
            await call.answer("✅ Allaqachon qo‘shilgan" if (user.lang or "uz") == "uz" else "✅ Уже в списке")
            return

        session.add(ClientBarbers(client_id=client.id, barber_id=barber_id))
        await session.commit()

    kb = barber_list_keyboard(user.lang or "uz", barber_id, True)
    text = "✅ Qo‘shildi" if (user.lang or "uz") == "uz" else "✅ Добавлено"
    await call.message.answer(text)
    await call.message.edit_reply_markup(reply_markup=kb)


@barber_profile.callback_query(F.data.startswith("removebarber:"))
async def remove_barber_cb(call: CallbackQuery):
    barber_id = int(call.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == call.from_user.id))
        ).scalar_one_or_none()
        if not user:
            await call.answer("❌ User not found", show_alert=True)
            return

        client = (
            await session.execute(select(Client).where(Client.user_id == user.id))
        ).scalar_one_or_none()
        if not client:
            await call.answer("❌ Client not found", show_alert=True)
            return

        row = (
            await session.execute(
                select(ClientBarbers).where(
                    ClientBarbers.client_id == client.id,
                    ClientBarbers.barber_id == barber_id
                )
            )
        ).scalar_one_or_none()

        if not row:
            await call.answer("ℹ️ Ro‘yxatda yo‘q" if (user.lang or "uz") == "uz" else "ℹ️ Не в списке")
            return

        await session.delete(row)
        await session.commit()

    kb = barber_list_keyboard(user.lang or "uz", barber_id, False)
    text = "🗑 O‘chirildi" if (user.lang or "uz") == "uz" else "🗑 Удалено"
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.message.answer(text)


@barber_profile.message(F.text.in_(["🗓️ Расписание барбера", "🗓️ Sartarosh jadvali"]))
async def barber_schedule(message: Message, state: FSMContext):
    tg_user = message.from_user
    today = datetime.now().date()
    end_date = today + timedelta(days=7)

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).options(selectinload(User.client)).where(User.telegram_id == tg_user.id)
            )
        ).scalar_one_or_none()

        if not user or not user.client:
            text = "Client topilmadi." if user and user.lang == "uz" else "Клиент не найден."
            await message.answer(text)
            return

        client = user.client

        client.selected_schedule_id = None
        await session.commit()

        barber = None
        if client.selected_barber:
            barber = (
                await session.execute(
                    select(Barber).where(Barber.id == client.selected_barber)
                )
            ).scalar_one_or_none()

        if not barber:
            text = "Barber topilmadi." if user.lang == "uz" else "Барбер не найден."
            await message.answer(text)
            return

        barber_working_days = [day.name_uz for day in barber.working_days if getattr(day, "is_working", False)]

        schedules = (
            await session.execute(
                select(BarberSchedule)
                .where(
                    BarberSchedule.barber_id == barber.id,
                    BarberSchedule.day.between(today, end_date),
                    BarberSchedule.name_uz.in_(barber_working_days),
                )
                .order_by(BarberSchedule.day.asc())
            )
        ).scalars().all()

    if not schedules:
        text = "❌ Jadval topilmadi." if user.lang == "uz" else "❌ Расписание не найдено."
        await message.answer(text)
        return

    text, keyboard = format_barber_schedule_days(schedules, user.lang)
    await message.answer(text, reply_markup=keyboard)


@barber_profile.callback_query(F.data.startswith("page:"))
async def paginate_schedule(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    schedules_ids = data.get("schedules", [])
    page = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        schedules = (
            await session.execute(
                select(BarberSchedule).where(BarberSchedule.id.in_(schedules_ids)).order_by(BarberSchedule.day.asc())
            )
        ).scalars().all()
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()

    await state.update_data(page=page)
    await send_schedule_page(callback, schedules, page, (user.lang if user and user.lang else "uz"))


@barber_profile.callback_query(F.data.startswith("barber_day:"))
async def barber_day_selected(callback: CallbackQuery, state: FSMContext):
    sched_id = int(callback.data.split(":")[1])
    lang = (await state.get_data()).get("lang", "uz")
    redis_pool = callback.bot.redis

    async with AsyncSessionLocal() as session:  # one session for the whole flow
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await callback.message.answer("❌ Пользователь не найден.")
            return

        client = (
            await session.execute(
                select(Client).where(Client.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not client:
            await callback.message.answer("❌ Клиент не найден.")
            return

        # save picked schedule
        client.selected_schedule_id = sched_id
        await session.commit()

        schedule = (
            await session.execute(
                select(BarberSchedule)
                .options(selectinload(BarberSchedule.details))
                .where(BarberSchedule.id == sched_id)
                .limit(1)
            )
        ).scalar_one_or_none()

        if not schedule:
            text = "❌ Jadval topilmadi." if lang == "uz" else "❌ Расписание не найдено."
            await callback.message.answer(text)
            return

        # build keyboard using the SAME session (no leak)
        base_kb = await kb_day_slots_by_sched_client(
            session=session,
            barber_id=schedule.barber_id,
            sched_id=sched_id,
            slot_minutes=30,
        )

    # after the context exits, the session is closed cleanly

    await redis_pool.set(f"user:{callback.from_user.id}:last_action", "barber_schedule")

    client_kb = kb_with_client_back(base_kb, lang)
    day_str = schedule.day.strftime('%d.%m.%Y')
    header = (
        f"📅 {day_str}\n🕒 Bo‘sh vaqtlar — slotni tanlang:"
        if lang == "uz"
        else f"📅 {day_str}\n🕒 Свободные слоты — выберите время:"
    )

    try:
        await callback.message.edit_text(header, reply_markup=client_kb)
    except Exception:
        await callback.message.answer(header, reply_markup=client_kb)


@barber_profile.callback_query(F.data == "barber_back")
async def barber_back(callback: CallbackQuery, state: FSMContext):
    today = datetime.now().date()
    end_date = today + timedelta(days=7)

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await callback.message.answer("❌ Пользователь не найден.")
            return

        client = (
            await session.execute(
                select(Client).where(Client.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not client:
            await callback.message.answer("❌ Клиент не найден.")
            return

        barber = (
            await session.execute(
                select(Barber)
                .options(selectinload(Barber.user))
                .where(Barber.id == client.selected_barber)
                .limit(1)
            )
        ).scalar_one_or_none()

        if not barber:
            text = "Barber topilmadi." if (user.lang or "uz") == "uz" else "Барбер не найден."
            await callback.message.answer(text)
            return
        barber_working_days = [day.name_uz for day in barber.working_days if getattr(day, "is_working", False)]

        schedules = (
            await session.execute(
                select(BarberSchedule)
                .where(
                    BarberSchedule.barber_id == barber.id,
                    BarberSchedule.day.between(today, end_date),
                    BarberSchedule.name_uz.in_(barber_working_days),
                )
                .order_by(BarberSchedule.day.asc())
            )
        ).scalars().all()

    if not schedules:
        await callback.message.answer(
            "❌ Jadval topilmadi." if (user.lang or "uz") == "uz" else "❌ Расписание не найдено."
        )
        return

    text, keyboard = format_barber_schedule_days(schedules, (user.lang or "uz"))
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
