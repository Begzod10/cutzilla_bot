from typing import Optional

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import AsyncSessionLocal
from app.user.models import User
from app.client.models import Client, ClientBarbers
from app.barber.models import Barber

# import your existing keyboard builder and translator
from .keyboards import make_my_barbers_keyboard

# from .i18n import _t  # if you have one; else use the fallback below

client_barber_list_router = Router()


# Fallback translator (remove if you already have _t)
def _t(lang: str, key: str) -> str:
    ru = (lang or "ru").lower().startswith("ru")
    RU = {
        "no_user": "❌ Пользователь не найден. Попробуйте /start.",
        "no_client": "❗️ Сначала зарегистрируйтесь как клиент.",
        "no_barbers": "🪮 У вас пока нет сохранённых барберов.",
        "title": "🪮 Мои барберы:",
    }
    UZ = {
        "no_user": "❌ Foydalanuvchi topilmadi. /start ni bosing.",
        "no_client": "❗️ Avval mijoz sifatida ro‘yxatdan o‘ting.",
        "no_barbers": "🪮 Sizda hozircha saqlangan barberlar yo‘q.",
        "title": "🪮 Mening barberlarim:",
    }
    return (RU if ru else UZ)[key]


@client_barber_list_router.message(F.text.in_(["🪮 Мои барберы", "🪮 Mening barberlarim"]))
async def client_barber_list(message: Message):
    tg_user = message.from_user

    async with AsyncSessionLocal() as session:
        # 1) Load platform User by telegram_id
        result_user = await session.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        db_user: Optional[User] = result_user.scalar_one_or_none()

        lang = getattr(db_user, "lang", "ru") if db_user else "ru"

        if not db_user:
            await message.answer(_t(lang, "no_user"))
            return

        # 2) Load Client by user_id
        result_client = await session.execute(
            select(Client).where(Client.user_id == db_user.id)
        )
        client: Optional[Client] = result_client.scalar_one_or_none()

        if not client:
            await message.answer(_t(lang, "no_client"))
            return

        # 3) Load saved barbers (prefetch Barber.user)
        result_cb = await session.execute(
            select(ClientBarbers)
            .where(ClientBarbers.client_id == client.id)
            .options(
                selectinload(ClientBarbers.barber).selectinload(Barber.user)
            )
        )
        client_barbers = result_cb.scalars().all()

    # 4) Respond
    if not client_barbers:
        await message.answer(_t(lang, "no_barbers"))
        return

    kb = make_my_barbers_keyboard(client_barbers, lang)
    await message.answer(_t(lang, "title"), reply_markup=kb)
