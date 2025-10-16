from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import CommandStart
from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.user.models import User
from app.client.models import Client
from app.barber.models import Barber
from .keyboards import client_main_menu, barber_main_menu, user_role_keyboard

commands_router = Router()


async def _load_user(session, tg_id: int):
    return (await session.execute(
        select(User).where(User.telegram_id == tg_id)
    )).scalar_one_or_none()


async def _get_role(session, user: User) -> str:
    """
    Returns 'barber', 'client', or 'unknown'
    """
    if not user:
        return "unknown"
    # barber?
    is_barber = (await session.execute(
        select(Barber.id).where(Barber.user_id == user.id)
    )).scalar_one_or_none()
    if is_barber:
        return "barber"
    # client?
    is_client = (await session.execute(
        select(Client.id).where(Client.user_id == user.id)
    )).scalar_one_or_none()
    if is_client:
        return "client"
    return "unknown"


@commands_router.message(F.text == "/profile")
async def cmd_profile(message: Message):
    async with AsyncSessionLocal() as session:
        user = await _load_user(session, message.from_user.id)
        lang = getattr(user, "lang", "uz") if user else "uz"
        role = await _get_role(session, user) if user else "unknown"

    if role == "barber":
        kb = barber_main_menu(lang)
        text = "👤 Profil: Barber" if lang != "ru" else "👤 Профиль: Барбер"
    elif role == "client":
        kb = client_main_menu(lang)
        text = "👤 Profil: Mijoz" if lang != "ru" else "👤 Профиль: Клиент"
    else:
        # Unknown role → default to client menu
        kb = client_main_menu(lang)
        text = ("👤 Profil topilmadi. Mijoz menyusi ko‘rsatildi."
                if lang != "ru" else
                "👤 Профиль не найден. Показано меню клиента.")

    await message.answer(text, reply_markup=kb)


HELP_UZ = (
    "🆘 *Yordam*\n"
    "• *Mijoz:* Xizmat tanla → bo‘sh slot → tasdiq → 🔔 eslatma.\n"
    "• *Barber:* Jadval, so‘rov qabul/rad, xizmatlarni yangilash.\n\n"
    "Buyruqlar: /profile /settings"
)

HELP_RU = (
    "🆘 *Помощь*\n"
    "• *Клиент:* Услуга → свободный слот → подтверждение → 🔔 напоминание.\n"
    "• *Барбер:* Расписание, заявки, обновление услуг.\n\n"
    "Команды: /profile /settings"
)


async def _get_lang(tg_id: int) -> str:
    async with AsyncSessionLocal() as session:
        user = (await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )).scalar_one_or_none()
        return getattr(user, "lang", "uz") if user else "uz"


@commands_router.message(F.text == "/help")
async def cmd_help(message: Message):
    lang = await _get_lang(message.from_user.id)
    text = HELP_RU if (lang or "").lower().startswith("ru") else HELP_UZ
    await message.answer(text, parse_mode="Markdown")


@commands_router.message(F.text == "/exit")
async def cmd_exit(message: Message, state: FSMContext):
    await state.clear()
    async with AsyncSessionLocal() as session:  # read-only
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()

        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi. Iltimos, qayta /start bosing.")
            return

        text = ("Вы успешно вышли из системы"
                if (user.lang or "uz").startswith("ru")
                else "Tizimdan muvaffaqiyatli chiqildingiz")

        await message.answer(text, reply_markup=user_role_keyboard(user.lang))
