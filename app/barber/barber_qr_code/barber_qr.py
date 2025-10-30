# handlers/barber_qr.py
from io import BytesIO
import qrcode
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.deep_linking import create_start_link
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db import AsyncSessionLocal
from app.models import User, Barber, Client
from .security import sign_barber_token
from app.barber.keyboards import barber_info_keyboard
from typing import Tuple, Optional
from .security import verify_barber_token
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from app.client.keyboards import barber_menu
from app.basic.task_sysnc_user import sync_client_to_django

barber_qr_route = Router()


async def _get_barber_by_tg_id(session, tg_id: int) -> Tuple[Optional[User], Optional[Barber]]:
    result_user = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: Optional[User] = result_user.scalar_one_or_none()
    if not user:
        return None, None

    result_barber = await session.execute(select(Barber).where(Barber.user_id == user.id))
    barber: Optional[Barber] = result_barber.scalar_one_or_none()

    return user, barber


@barber_qr_route.message(F.text.in_({"🧾 Сгенерировать QR", "🧾 QR kod yaratish"}))
async def on_generate_qr(message: Message):
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one_or_none()
        barber = None
        if user:
            barber_res = await session.execute(select(Barber).where(Barber.user_id == user.id))
            barber = barber_res.scalar_one_or_none()

    lang = (user.lang if user and getattr(user, "lang", None) else "ru") if user else "ru"

    if not user:
        await message.answer("❌ Пользователь не найден." if lang == "ru" else "❌ Foydalanuvchi topilmadi.")
        return
    if not barber:
        await message.answer(
            "❗ Эта функция доступна только барберам." if lang == "ru" else "❗ Bu funksiya faqat barberlar uchun.")
        return

    # 2) Compact deep link token (≤64 chars)
    token = sign_barber_token(barber.id)

    # IMPORTANT: we already pre-encoded → use encode=False
    deep_link = await create_start_link(message.bot, payload=token, encode=False)

    # 3) QR in-memory
    buf = BytesIO()
    qrcode.make(deep_link).save(buf, format="PNG")
    buf.seek(0)

    # 4) Caption
    if lang == "uz":
        cap = (
            "✂️ Sizning QR havolangiz tayyor!\n\n"
            # f"🔗 Havola: {deep_link}\n\n"
            "📌 Mijozlar ushbu QR kodni skaner qilib, profilingizga darhol kirishi mumkin."
        )
    else:
        cap = (
            "✂️ Ваш QR-код готов!\n\n"
            # f"🔗 Ссылка: {deep_link}\n\n"
            "📌 Клиенты могут отсканировать этот QR, чтобы сразу открыть ваш профиль в боте."
        )

    await message.answer_photo(
        photo=BufferedInputFile(buf.read(), filename=f"barber_{barber.id}_qr.png"),
        caption=cap,
        reply_markup=barber_info_keyboard(lang)
    )


@barber_qr_route.message(CommandStart(deep_link=True))
async def start_from_qr(message: Message, command: CommandObject):
    payload = (command.args or "").strip()
    barber_id = verify_barber_token(payload)
    redis_pool = message.bot.redis
    if not barber_id:
        await message.answer("❗ Неверная или просроченная ссылка.")
        return

    # Ensure user & client exist (idempotent)
    from_user = message.from_user
    user, client = await get_or_create_user_and_client(
        tg_id=from_user.id,
        first_name=from_user.first_name,
        last_name=from_user.last_name,
        username=from_user.username,
        lang_code=from_user.language_code,
    )

    # Load target barber
    async with AsyncSessionLocal() as session:
        barber = (await session.execute(select(Barber).where(Barber.id == barber_id))).scalar_one_or_none()
        if not barber:
            text = "Barber topilmadi." if (user.lang or "uz") == "uz" else "Барбер не найден."
            await message.answer(text)
            return

        # Persist selection: set user's selected barber
        client.selected_barber = barber_id
        await session.merge(client)  # ensure attached to this session
        await session.commit()

        # Prepare response fields
        barber_name = barber.user.name if barber.user else ""
        barber_surname = barber.user.surname if barber.user else ""
        barber_score = barber.score or "—"

    # Optional: breadcrumb in Redis
    if hasattr(message.bot, "redis") and message.bot.redis:
        await message.bot.redis.set(f"user:{user.telegram_id}:last_action", "barber_profile")
    await redis_pool.set(f"user:{user.telegram_id}:last_action", "barber_profile")
    lang = user.lang or normalize_lang(from_user.language_code)
    text = "Siz tanlagan barber:" if lang == "uz" else "Вы выбрали барбера:"
    await message.answer(
        f"{text} {barber_name} {barber_surname} ⭐ {barber_score}",
        reply_markup=barber_menu(lang),
    )


def normalize_lang(code: Optional[str]) -> str:
    if not code:
        return "ru"
    code = code.lower()
    if code.startswith("uz"):
        return "uz"
    if code.startswith("ru"):
        return "ru"
    return "ru"


async def get_or_create_user_and_client(
        tg_id: int,
        first_name: Optional[str],
        last_name: Optional[str],
        username: Optional[str],
        lang_code: Optional[str],
) -> Tuple[User, Client]:
    async with AsyncSessionLocal() as session:
        # 1) user
        res = await session.execute(select(User).where(User.telegram_id == tg_id))
        user: Optional[User] = res.scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=tg_id,
                name=first_name or "",
                surname=last_name or "",
                platform_login=username or None,
                lang=normalize_lang(lang_code),
            )
            session.add(user)
            try:
                await session.flush()  # get user.id
            except IntegrityError:
                await session.rollback()
                # race: someone created user concurrently, refetch
                user = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one()

        # 2) client
        res = await session.execute(select(Client).where(Client.user_id == user.id).limit(1))
        client: Optional[Client] = res.scalar_one_or_none()
        if not client:
            client = Client(user_id=user.id)
            session.add(client)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                client = (await session.execute(select(Client).where(Client.user_id == user.id).limit(1))).scalar_one()
        sync_client_to_django.delay(
            telegram_id=tg_id,
            first_name=user.name,
            last_name=user.surname,
            lang=normalize_lang(lang_code),
            role="client",
            client_id=client.id
        )
        user.user_type = "client"
        await session.commit()
        return user, client
