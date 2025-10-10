from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.barber.models import Barber
from app.user.models import User
from .keyboards import barber_map_keyboard, location_request_keyboard
from app.basic.keyboards import back_keyboard
from app.states import ChangeLocation, EditAddress
from app.client.utils import get_region_city_multilang

import os

barber_location = Router()


@barber_location.message(F.text.in_(['📍 Manzil', '📍 Локация']))
async def get_location(message: Message, state: FSMContext):
    lang = "ru" if message.text == "📍 Локация" else "uz"
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        # user
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi." if lang == "uz" else "❌ Пользователь не найден.")
            return

        # barber
        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()

    await redis_pool.set(f"user:{message.from_user.id}:last_action", "barber_location")

    if barber and barber.latitude and barber.longitude:
        await message.answer_venue(
            latitude=barber.latitude,
            longitude=barber.longitude,
            title=barber.location_title or ("Мой салон" if lang == "ru" else "Mening salonim"),
            address=barber.address or ("Адрес не указан" if lang == "ru" else "Manzil kiritilmagan")
        )
        await message.answer(".", reply_markup=barber_map_keyboard(lang))
    else:
        await message.answer(
            "❌ Локация не найдена" if lang == "ru" else "❌ Joylashuv topilmadi",
            reply_markup=barber_map_keyboard(lang)
        )


@barber_location.message(F.text.in_(["✏️ Joylashuvni o'zgartirish", "✏️ Изменить локацию"]))
async def ask_for_location(message: Message, state: FSMContext):
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

    lang = (user.lang if user else "uz")
    await redis_pool.set(f"user:{message.from_user.id}:last_action", "barber_location_change")

    text = "✏️ Joylashuvni o'zgartirish" if lang == "uz" else "✏️ Изменить локацию"
    await message.answer(text, reply_markup=location_request_keyboard(lang))
    await state.set_state(ChangeLocation.waiting_for_location)


@barber_location.message(ChangeLocation.waiting_for_location, F.location)
async def save_barber_location(message: Message, state: FSMContext):
    latitude = message.location.latitude
    longitude = message.location.longitude

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

        barber = (
            await session.execute(
                select(Barber).where(
                    Barber.user_id == user.id, Barber.login == user.platform_login
                )
            )
        ).scalar_one_or_none()

        # 🔹 call the new Yandex-backed function
        country, region, city = await get_region_city_multilang(session, latitude, longitude)

        # Save on user
        user.country_id = country.id
        user.region_id = region.id
        user.city_id = city.id

        # Save on barber
        barber.latitude = latitude
        barber.longitude = longitude

        await session.commit()

        await message.answer(
            "✅ Joylashuv saqlandi!" if user.lang == "uz" else "✅ Локация сохранена!",
            reply_markup=barber_map_keyboard(user.lang),
        )
        await message.answer_location(latitude=latitude, longitude=longitude)

    await state.clear()



@barber_location.message(ChangeLocation.waiting_for_location)
async def invalid_location(message: Message):
    await message.answer(
        "❗ Iltimos, joylashuvni yuboring 📍" if (message.from_user.language_code or "uz") == "uz"
        else "❗ Пожалуйста, отправьте локацию 📍"
    )


@barber_location.message(F.text.in_(["✏️ Manzilni o'zgartirish", "✏️ Изменить адрес"]))
async def ask_new_address(message: Message, state: FSMContext):
    lang = "ru" if message.text == "✏️ Изменить адрес" else "uz"
    await message.answer("Yangi manzilingizni kiriting:" if lang == "uz" else "Введите новый адрес:")
    await state.set_state(EditAddress.waiting_for_address)


@barber_location.message(EditAddress.waiting_for_address)
async def save_new_address(message: Message, state: FSMContext):
    new_address = (message.text or "").strip()

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
            await message.answer("❌ Sartarosh topilmadi." if (user.lang or "uz") == "uz" else "❌ Барбер не найден.")
            return

        barber.address = new_address
        await session.commit()

        lang = user.lang or "uz"
        await message.answer(
            "✅ Manzil yangilandi." if lang == "uz" else "✅ Адрес обновлен.",
            reply_markup=barber_map_keyboard(lang)
        )

        if barber.latitude and barber.longitude:
            await message.answer_venue(
                latitude=barber.latitude,
                longitude=barber.longitude,
                title=barber.location_title or ("Мой салон" if lang == "ru" else "Mening salonim"),
                address=barber.address or ("Адрес не указан" if lang == "ru" else "Manzil kiritilmagan")
            )

    await state.clear()


@barber_location.message(F.text.in_(["✏️ Salon nomini o'zgartirish", "✏️ Изменить название салона"]))
async def change_barber_name(message: Message, state: FSMContext):
    lang = "ru" if message.text == "✏️ Изменить название салона" else "uz"
    await message.answer("Salon nomini kiriting:" if lang == "uz" else "Введите название салона:")
    await state.set_state(EditAddress.waiting_for_location_name)


@barber_location.message(EditAddress.waiting_for_location_name)
async def save_location_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()

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
            await message.answer("❌ Sartarosh topilmadi." if (user.lang or "uz") == "uz" else "❌ Барбер не найден.")
            return

        barber.location_title = title
        await session.commit()

        lang = user.lang or "uz"
        await message.answer(
            "✅ Salon nomi yangilandi." if lang == "uz" else "✅ Название салона обновлено.",
            reply_markup=barber_map_keyboard(lang)
        )

        if barber.latitude and barber.longitude:
            await message.answer_venue(
                latitude=barber.latitude,
                longitude=barber.longitude,
                title=barber.location_title or ("Мой салон" if lang == "ru" else "Mening salonim"),
                address=barber.address or ("Адрес не указан" if lang == "ru" else "Manzil kiritilmagan")
            )

    await state.clear()
