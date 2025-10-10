from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from datetime import datetime

from app.db import AsyncSessionLocal
from app.barber.models import Barber
from app.user.models import User
from .keyboards import working_time_keyboard
from app.states import WorkingTime

barber_working_time = Router()


@barber_working_time.message(F.text.in_(["🕒 Ish vaqti", "🕒 Время работы"]))
async def working_time(message: Message, state: FSMContext):
    # keep your generic marker; you already use named states later
    await state.set_state("working_time")
    redis_pool = message.bot.redis

    # load user + barber
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi.")
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()

    lang = (user.lang or "uz") if user else "uz"
    if not barber:
        await message.answer("Sartarosh topilmadi." if lang == "uz" else "Барбер не найден.")
        return

    start = (
        barber.start_time.strftime("%H:%M")
        if getattr(barber, "start_time", None)
        else ("belgilanmagan" if lang == "uz" else "не указано")
    )
    end = (
        barber.end_time.strftime("%H:%M")
        if getattr(barber, "end_time", None)
        else ("belgilanmagan" if lang == "uz" else "не указано")
    )

    # save last action in redis
    await redis_pool.set(f"user:{message.from_user.id}:last_action", "barber_working_time")

    text = (
        f"🕒 Ish vaqti:\n⏰ Boshlanishi: {start}\n⏰ Tugashi: {end}"
        if lang == "uz"
        else f"🕒 Время работы:\n⏰ Начало: {start}\n⏰ Конец: {end}"
    )
    await message.answer(text, reply_markup=working_time_keyboard(lang))


@barber_working_time.message(F.text.in_(["⏱ Vaqt belgilash", "⏱ Установить время"]))
async def start_setting_time(message: Message, state: FSMContext):
    lang = "ru" if message.text.startswith("⏱ У") else "uz"
    await state.update_data(lang=lang)
    text = (
        "🕒 Boshlanish vaqtini kiriting (masalan, 09:00):"
        if lang == "uz"
        else "🕒 Введите время начала (например, 09:00):"
    )
    await message.answer(text)
    await state.set_state(WorkingTime.waiting_for_start)


@barber_working_time.message(WorkingTime.waiting_for_start)
async def handle_start_time(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    try:
        start_time_obj = datetime.strptime(message.text.strip(), "%H:%M").time()
    except ValueError:
        await message.answer(
            "❌ Format noto‘g‘ri. Masalan: 09:00" if lang == "uz" else "❌ Неверный формат. Например: 09:00"
        )
        await state.set_state(WorkingTime.waiting_for_start)
        return

    await state.update_data(start_time=start_time_obj.strftime("%H:%M"))  # store as string
    text = (
        "🕒 Tugash vaqtini kiriting (masalan, 18:00):"
        if lang == "uz"
        else "🕒 Введите время окончания (например, 18:00):"
    )
    await message.answer(text)
    await state.set_state(WorkingTime.waiting_for_end)


@barber_working_time.message(WorkingTime.waiting_for_end)
async def handle_end_time(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    # parse end time
    try:
        end_time = datetime.strptime(message.text.strip(), "%H:%M").time()
    except ValueError:
        await message.answer(
            "❌ Format noto‘g‘ri. Masalan: 18:00" if lang == "uz" else "❌ Неверный формат. Например: 18:00"
        )
        return

    # get previously entered start time
    start_time_str = data.get("start_time")
    if not start_time_str:
        await message.answer(
            "❗ Avval boshlanish vaqtini kiriting." if lang == "uz" else "❗ Сначала укажите время начала."
        )
        await state.set_state(WorkingTime.waiting_for_start)
        return

    try:
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
    except ValueError:
        await message.answer(
            "❗ Boshlanish vaqti yaroqsiz. Qaytadan kiriting." if lang == "uz"
            else "❗ Неверное время начала. Введите заново."
        )
        await state.set_state(WorkingTime.waiting_for_start)
        return

    # store in DB
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi.")
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            await message.answer("Sartarosh topilmadi." if lang == "uz" else "Барбер не найден.")
            return

        # Your model stores datetimes; keep that behavior (combine with today)
        barber.start_time = datetime.combine(datetime.today(), start_time)
        barber.end_time = datetime.combine(datetime.today(), end_time)
        await session.commit()

    start_str = start_time.strftime("%H:%M")
    end_str = end_time.strftime("%H:%M")

    await message.answer(
        "✅ Ish vaqti saqlandi!" if lang == "uz" else "✅ Время работы сохранено!",
        reply_markup=working_time_keyboard(lang),
    )

    text = (
        f"🕒 Ish vaqti:\n⏰ Boshlanishi: {start_str}\n⏰ Tugashi: {end_str}"
        if lang == "uz"
        else f"🕒 Время работы:\n⏰ Начало: {start_str}\n⏰ Конец: {end_str}"
    )
    await message.answer(text)
    await state.clear()
