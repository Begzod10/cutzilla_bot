from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

# ✅ make sure you import your async session factory
# e.g., from app.core.db import AsyncSessionLocal
from app.db import AsyncSessionLocal

from app.states import ChangeLocation
from app.user.models import User
from .keyboards import location_keyboard
from .utils import get_region_city_multilang  # async version: (session, lat, lon) -> (Country, Region, City)

client_basic = Router()


@client_basic.message(F.text.in_({"📍 Отправить мою локацию", "📍 Lokatsiyamni yuborish"}))
async def send_location(message: Message, state: FSMContext):
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        tg_user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

        if not tg_user:
            await message.answer(
                "❌ Foydalanuvchi topilmadi."
                if (message.from_user.language_code or "uz").startswith("uz")
                else "❌ Пользователь не найден."
            )
            return

        tg_user.user_type = "client"
        await session.commit()

    # store last action in Redis (async)
    await redis_pool.set(f"user:{message.from_user.id}:last_action", "client_location")

    await message.answer(
        ".",
        reply_markup=location_keyboard(tg_user.lang if tg_user.lang else "uz")
    )
    await state.set_state(ChangeLocation.location_for_client)


@client_basic.message(ChangeLocation.location_for_client, F.location)
async def save_client_location(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude

    async with AsyncSessionLocal() as session:
        # fetch user
        tg_user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

        if not tg_user:
            await message.answer(
                "❌ Foydalanuvchi topilmadi."
                if (message.from_user.language_code or "uz").startswith("uz")
                else "❌ Пользователь не найден."
            )
            return

        # 🔹 Reverse-geocode via Yandex (UZ/RU) and upsert Country/Region/City
        print(lat, lon)
        country, region, city = await get_region_city_multilang(session, lat, lon)

        # Save location if found
        if city and region and country:
            tg_user.country_id = country.id
            tg_user.region_id = region.id
            tg_user.city_id = city.id

            await session.commit()

            lang = (tg_user.lang or "uz").lower()
            city_name = city.name_uz if lang == "uz" else city.name_ru
            region_name = region.name_uz if lang == "uz" else region.name_ru
            country_name = country.name_uz if lang == "uz" else country.name_ru

            text = (
                f"📍 Shahar: {city_name}\n🏙 Viloyat: {region_name}\n🌍 Davlat: {country_name}"
                if lang == "uz"
                else f"📍 Город: {city_name}\n🏙 Регион: {region_name}\n🌍 Страна: {country_name}"
            )
            await message.answer(text)
        else:
            text = (
                "❌ Kechirasiz, sizning manzilingizni aniqlab bo‘lmadi. Iltimos, qayta yuboring yoki qo‘lda kiriting."
                if (tg_user.lang or "uz") == "uz"
                else "❌ Извините, не удалось определить ваше местоположение. Пожалуйста, отправьте снова или введите вручную."
            )
            await message.answer(text)

    await state.clear()
