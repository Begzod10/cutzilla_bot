from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import os
import httpx

from app.states import LoginState
from app.user.models import User
from .keyboards import (
    language_keyboard, get_login_keyboard, user_role_keyboard,
    barber_main_menu, back_keyboard, client_main_menu
)
from .text import TEXTS, LOGIN_TEXT

from app.barber.models import Barber, BarberService, BarberWorkingDays
from app.service.models import Service
from app.barber.keyboards import (
    barber_services_keyboard, barber_service_menu_keyboard,
    barber_info_keyboard, barber_map_keyboard
)
from app.client.keyboards import location_keyboard, barber_menu
from .task_sysnc_user import _enqueue_user_sync, sync_client_to_django
from app.redis_client import redis_client
from app.client.models import Client
from app.db import AsyncSessionLocal

router = Router()


@router.message(F.text == "reset")
async def reset_state(message: Message, state: FSMContext):
    await state.clear()

    # Guard in case storages differ
    if getattr(state.storage, "redis", None):
        await state.storage.redis.flushdb()
    if getattr(message.bot, "redis", None):
        await message.bot.redis.flushdb()

    await message.answer("✅ All Redis sessions and FSM states cleared.")
    await message.answer("✅ Your state has been cleared.")


@router.message(F.text.in_(["🌐 Tilni o‘zgartirish", "🌐 Сменить язык"]))
async def set_language(message: Message):
    tg_id = message.from_user.id
    redis_pool = message.bot.redis
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = user.scalar_one_or_none()

    await redis_pool.set(f"user:{tg_id}:last_action", "waiting_for_username")
    await message.answer(
        "Iltimos, tilni tanlang / Пожалуйста, выберите язык:",
        reply_markup=language_keyboard
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Iltimos, tilni tanlang / Пожалуйста, выберите язык:",
        reply_markup=language_keyboard
    )


@router.message(F.text.in_({"🇺🇿 UZ", "🇷🇺 RU"}))
async def choose_language(message: Message, state: FSMContext):
    lang_map = {"🇺🇿 UZ": "uz", "🇷🇺 RU": "ru"}
    lang_code = lang_map.get(message.text)
    if not lang_code:
        await message.answer("Til aniqlanmadi / Язык не распознан")
        return

    await state.update_data(lang=lang_code)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            user = await session.scalar(
                select(User).where(User.telegram_id == message.from_user.id)
            )

            if user:
                # UPDATE path
                user.lang = lang_code
                role_for_django = "barber" if user.user_type == "barber" else "user"
                reply_markup = (
                    barber_main_menu(user.lang)
                    if user.user_type == "barber"
                    else client_main_menu(user.lang)
                )
                text = "Til o'zgartirildi" if user.lang == "uz" else "Язык изменен"

            else:
                # CREATE path
                user = User(
                    telegram_id=message.from_user.id,
                    name=message.from_user.first_name,
                    surname=message.from_user.last_name,
                    lang=lang_code,
                )
                session.add(user)
                await session.flush()  # <-- ensures user.id is available

                # set relationship (or use user_id=user.id) and safe defaults
                client = Client(user=user, score=0, blocked=False)
                session.add(client)

                reply_markup = client_main_menu(lang_code)
                text = None  # we'll send welcome text below
    welcome_text = TEXTS[lang_code]["welcome"]
    if text:
        await message.answer(text, reply_markup=reply_markup)
    else:
        await message.answer(welcome_text, parse_mode="HTML", reply_markup=reply_markup)

    # enqueue sync AFTER commit
    role_for_django = "barber" if getattr(user, "user_type", None) == "barber" else "user"
    await _enqueue_user_sync({
        "telegram_id": message.from_user.id,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "role": role_for_django,
        "username": message.from_user.username or str(message.from_user.id),
    })



ROLE_MAP = {
    "👤 Mijoz": "client",
    "👤 Клиент": "client",
    "✂️ Sartarosh": "barber",
    "✂️ Парикмахер": "barber",
}


@router.message(F.text.in_(list(ROLE_MAP.keys())))
async def handle_user_role_selection(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    role = ROLE_MAP.get(message.text)
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = res.scalar_one_or_none()
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi. Iltimos, qayta /start bosing.")
            return

        lang = (user.lang or "uz").lower()

        if role == "client":
            # set role
            user.user_type = "client"
            await session.commit()
            # ensure Client exists
            exist_client_id = (
                await session.execute(
                    select(Client.id).where(Client.user_id == user.id).limit(1)
                )
            ).scalar_one_or_none()

            if exist_client_id is None:
                client = Client(user_id=user.id)
                session.add(client)
                await session.commit()
                await session.flush()  # ← gets PK from DB
                client_id = client.id
            else:
                client_id = exist_client_id
            sync_client_to_django.delay(
                telegram_id=tg_id,
                first_name=user.name,
                last_name=user.surname,
                lang=lang,
                role="client",
                client_id=client_id
            )

    # Replies after commit
    if role == "client":
        keyboard = client_main_menu(lang)
        msg = "✅ Вы выбрали роль клиента." if lang.startswith("ru") else "✅ Siz mijoz sifatida tanlandingiz."
        await message.answer(msg, reply_markup=keyboard)
    else:
        msg = "✂️ Вы выбрали роль парикмахера." if lang.startswith("ru") else "✂️ Siz sartarosh sifatida tanlandingiz."
        await message.answer(msg)

        prompt = "📝 Пожалуйста, введите ваше имя пользователя:" if lang.startswith("ru") \
            else "📝 Iltimos, usernameni kiriting:"
        keyboard = back_keyboard(lang)
        await message.answer(prompt, reply_markup=keyboard)

        # Keep last_action aligned with FSM
        await redis_pool.set(f"user:{tg_id}:last_action", "waiting_for_username")
        await state.set_state(LoginState.waiting_for_username)


@router.message(F.text.in_({"⬅️ Orqaga", "⬅️ Назад"}))
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    tg_id = message.from_user.id
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:  # read-only
        # --- Load user
        user_res = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = user_res.scalar_one_or_none()
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi. Iltimos, qayta /start bosing.")
            return

        lang = (user.lang or "uz").lower()
        is_ru = lang.startswith("ru")

        # --- Read last_action from Redis and normalize
        action = await redis_pool.get(f"user:{user.telegram_id}:last_action")
        if isinstance(action, bytes):
            action = action.decode("utf-8")
        if action is None:
            action = "root"

        keyboard = None
        if user.user_type == "barber":
            if action in {"show_roles", "waiting_for_username"}:
                keyboard = user_role_keyboard(lang)

            elif action == "barber_services":
                keyboard = barber_main_menu(lang)

            elif action in {"add_service", "service_profile", "barber_service"}:
                # Get barber
                barber_res = await session.execute(
                    select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login).limit(1)
                )
                barber = barber_res.scalar_one_or_none()

                if barber:
                    svc_res = await session.execute(
                        select(BarberService).where(BarberService.barber_id == barber.id,
                                                    BarberService.is_active == True)
                    )
                    services = list(svc_res.scalars().all())
                else:
                    services = []

                await message.answer(
                    "Ваши услуги:" if is_ru else "Xizmatlaringiz ro'yxati:",
                    reply_markup=barber_services_keyboard(services, lang)
                )

                keyboard = barber_service_menu_keyboard(lang)
                await redis_pool.set(f"user:{user.telegram_id}:last_action", "barber_services")

            elif action == "barber_info":
                keyboard = barber_main_menu(lang)

            elif action in {"barber_resume", "barber_photo", "barber_working_time", "barber_location"}:
                await redis_pool.set(f"user:{user.telegram_id}:last_action", "barber_info")
                keyboard = barber_info_keyboard(lang)

            elif action == "barber_location_change":
                await redis_pool.set(f"user:{user.telegram_id}:last_action", "barber_location")
                keyboard = barber_map_keyboard(lang)

            else:
                keyboard = barber_main_menu(lang)

        elif user.user_type == "client":
            if action in {"client_barber_selection", "client_location", "barber_profile", "root"}:
                keyboard = client_main_menu(lang)

            elif action == "barber_schedule":
                await redis_pool.set(f"user:{user.telegram_id}:last_action", "barber_profile")
                keyboard = barber_menu(lang)

            elif action == "request_profile":
                await redis_pool.set(f"user:{user.telegram_id}:last_action", "barber_schedule")
                keyboard = barber_menu(lang)

            else:
                keyboard = client_main_menu(lang)

    text = "⬅️ Вы вернулись назад" if is_ru else "⬅️ Ortga qaytdingiz"
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text.in_({"🔐 Chiqish", "🔐 Выход"}))
async def logout(message: Message, state: FSMContext):
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


@router.message(LoginState.waiting_for_username)
async def get_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    tg_id = message.from_user.id

    async with AsyncSessionLocal() as session:  # read-only
        res = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = res.scalar_one_or_none()
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi. Iltimos, qayta /start bosing.")
            return

        lang = user.lang or "uz"

    text = "🔑 Теперь <b>ваш пароль</b>:" if (lang or "uz").startswith("ru") else "🔑 Endi <b>parolingizni</b> kiriting:"
    await message.answer(text, parse_mode="HTML")
    await state.set_state(LoginState.waiting_for_password)


@router.message(LoginState.waiting_for_password)
async def get_password(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    user_data = await state.get_data()
    username = user_data.get("username")
    password = message.text
    api = os.getenv("API")

    # Call external API
    ok = False
    payload = {}
    try:
        async with httpx.AsyncClient() as client:
            login_response = await client.post(
                f"{api}/api/v1/auth/login/",
                json={"login": username, "password": password, "telegram_id": telegram_id},
                timeout=10
            )
        ok = (login_response.status_code == 200)
        payload = login_response.json() if ok else {}
    except Exception:
        ok = False
        payload = {}

    # Load user (read-only)
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Iltimos, qayta /start bosing.")
        return

    lang = (user.lang or "uz").lower()
    is_ru = lang.startswith("ru")
    barber_data = payload.get("barber") if ok else None
    if not barber_data:
        text = ("❌ Неверное имя пользователя или пароль.\nПожалуйста, попробуйте ещё раз."
                if is_ru else
                "❌ Parol yoki foydalanuvchi nomi noto'g'ri.\nIltimos, qayta urinib ko'ring.")
        await message.answer(text)
        await state.set_state(LoginState.waiting_for_username)
        return

    # Persist login info + upsert barber/services
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Reload user for write
            res = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = res.scalar_one_or_none()
            if not user:
                raise RuntimeError("User disappeared during login flow")

            user.platform_login = username
            user.user_type = "barber"
            # Ensure Barber exists
            res = await session.execute(
                select(Barber).filter(Barber.user_id == user.id).limit(1))
            barber = res.scalar_one_or_none()

            if not barber:
                barber = Barber(
                    user_id=user.id,
                    login=username
                )
                session.add(barber)
                await session.flush()  # populate barber.id
            user.platform_id = payload.get("user_id")
            user.user_type = "barber"
            barber.user_id = user.id
            barber.login = username
            await session.commit()
    await state.clear()
    await message.answer(LOGIN_TEXT[lang]["welcome"], reply_markup=barber_main_menu(lang))
