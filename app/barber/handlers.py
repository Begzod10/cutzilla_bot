from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.db import AsyncSessionLocal  # ← make sure this path is correct
from app.user.models import User
from app.barber.models import Barber, BarberService
from .keyboards import (
    barber_services_keyboard,
    barber_service_menu_keyboard,
    barber_info_keyboard,
)

barber_router = Router()


@barber_router.message(F.text.in_(["✂️ Mening xizmatlarim", "✂️ Мои услуги"]))
async def show_services(message: Message, state: FSMContext):
    await state.clear()
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        # user
        user_obj = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

        if not user_obj:
            await message.answer(
                "Foydalanuvchi topilmadi." if message.from_user.language_code == "uz" else "Пользователь не найден.")
            return

        await redis_pool.set(f"user:{user_obj.telegram_id}:last_action", "barber_services")
        lang = user_obj.lang or "uz"

        # barber
        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user_obj.id, Barber.login == user_obj.platform_login)
            )
        ).scalar_one_or_none()

        if not barber:
            await message.answer("Sartarosh topilmadi." if lang == "uz" else "Парикмахер не найден.")
            return

        # services
        services = (
            await session.execute(
                select(BarberService).where(BarberService.barber_id == barber.id, BarberService.is_active == True)
            )
        ).scalars().all()

        if not services:
            await message.answer(
                "Siz hali xizmat qo‘shmagansiz." if lang == "uz" else "У вас пока нет услуг.",
                reply_markup=barber_service_menu_keyboard(lang),
            )
            return

        await message.answer(
            "Xizmatlaringiz ro'yxati:" if lang == "uz" else "Ваши услуги:",
            reply_markup=barber_services_keyboard(services, lang),
        )
        # Small follow-up menu message (emoji only, as in your original)
        await message.answer("📋", reply_markup=barber_service_menu_keyboard(lang))


@barber_router.message(F.text.in_(['ℹ️ Ma’lumot', 'ℹ️ Информация']))
async def show_info(message: Message):
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        user_obj = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

        if not user_obj:
            await message.answer(
                "Foydalanuvchi topilmadi." if message.from_user.language_code == "uz" else "Пользователь не найден.")
            return

        await redis_pool.set(f"user:{user_obj.telegram_id}:last_action", "barber_info")

        lang = user_obj.lang or "uz"
        text = "Shaxsiy ma'lumotlar:" if lang == "uz" else "Личные данные:"
        await message.answer(text, reply_markup=barber_info_keyboard(lang))
