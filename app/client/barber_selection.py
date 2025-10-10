from aiogram import F, Router

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from sqlalchemy import desc
from sqlalchemy.orm import lazyload, selectinload

from app.user.models import User
from app.barber.models import Barber
from app.client.models import Client

from app.region.models import Region, City
from math import ceil
from .keyboards import (
    make_barbers_keyboard_rows, create_regions_keyboard, _t,
    create_cities_keyboard, create_back_to_cities_keyboard,
    InlineKeyboardMarkup, barber_menu
)

from app.db import AsyncSessionLocal
from sqlalchemy import select

client_barber_selection = Router()
PAGE_SIZE = 10


@client_barber_selection.message(F.text.in_(["✂️ Барберы", "✂️ Barberlar"]))
async def select_barber(message: Message, state: FSMContext):
    tg_user_id = message.from_user.id
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        # Single roundtrip: get user fields + client id
        res = await session.execute(
            select(
                User.id, User.lang, User.city_id, User.region_id,
                Client.id.label("client_id")
            )
            .join(Client, Client.user_id == User.id, isouter=True)
            .where(User.telegram_id == tg_user_id)
            .limit(1)
        )
        row = res.first()
        if not row:
            await message.answer("❌ Пользователь не найден.")
            return

        user_id, lang, city_id, region_id, client_id = row
        lang = lang or "ru"

        if not client_id:
            await message.answer("❌ Клиент не найден.")
            return

        # If location missing → show regions
        if not region_id or not city_id:
            regions = (await session.execute(select(Region).order_by(Region.id))).scalars().all()
            # if not regions:
            #     await message.answer(_t(lang, "❌ Регионов не найдено.", "❌ Hech qanday region topilmadi."))
            #     return
            await message.answer(
                _t(lang, "Выберите регион:", "Regionni tanlang:"),
                reply_markup=create_regions_keyboard(regions, lang)
            )
            return

        # Count & first page (columns-only)
        total_ids = (await session.execute(
            select(Barber.id)
            .join(User, Barber.user_id == User.id)
            .where(User.city_id == city_id)
        )).all()
        total_count = len(total_ids)
        total_pages = max(1, ceil(total_count / PAGE_SIZE))

        page = 1
        await state.update_data(barbers_page=page)

        rows = (await session.execute(
            select(Barber.id, Barber.score, User.name, User.surname)
            .join(User, Barber.user_id == User.id)
            .where(User.city_id == city_id)
            .order_by(desc(Barber.score))
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
        )).all()

    await redis_pool.set(f"user:{tg_user_id}:last_action", "client_barber_selection")

    if not rows:
        async with AsyncSessionLocal() as session:
            regions = (await session.execute(select(Region).order_by(Region.id))).scalars().all()
        await message.answer(
            _t(lang, "😔 В вашем городе пока нет барберов.", "😔 Sizning shahringizda hozircha barber yo‘q.")
        )
        await message.answer(
            _t(lang, "Выберите регион:", "Regionni tanlang:"),
            reply_markup=create_regions_keyboard(regions, lang)
        )
        return

    kb = make_barbers_keyboard_rows(rows, lang, page, total_pages, include_filter_button=True)
    await message.answer(_t(lang, "Выберите барбера:", "Barberni tanlang:"), reply_markup=kb)


@client_barber_selection.callback_query(F.data.startswith("barbers_page:"))
async def paginate_barbers(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id
    new_page = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == tg_user_id))).scalar_one_or_none()
        lang = getattr(user, "lang", "ru") if user else "ru"

        data = await state.get_data()
        selected_city_id = data.get("selected_city_id")
        city_id = selected_city_id or (user.city_id if user else None)

        if not city_id:
            # Fall back to regions if we can’t determine city
            regions = (await session.execute(select(Region).order_by(Region.id))).scalars().all()
            await callback.message.edit_text(
                _t(lang, "Выберите регион:", "Regionni tanlang:"),
                reply_markup=create_regions_keyboard(regions, lang)
            )
            await callback.answer()
            return

        # Recompute total for the current scope (selected city or user city)
        total_q = select(Barber.id).join(User, Barber.user_id == User.id).where(User.city_id == city_id)
        total = (await session.execute(total_q)).all()
        total_count = len(total)
        total_pages = max(1, ceil(total_count / PAGE_SIZE))

        page = max(1, min(new_page, total_pages))
        await state.update_data(barbers_page=page)

        # Page query using only required columns
        stmt = (
            select(Barber.id, Barber.score, User.name, User.surname)
            .join(User, Barber.user_id == User.id)
            .where(User.city_id == city_id)
            .order_by(desc(Barber.score))
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
        )
        rows = (await session.execute(stmt)).all()

    kb = make_barbers_keyboard_rows(rows, lang, page, total_pages, include_filter_button=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        await callback.message.edit_text(
            _t(lang, "Выберите барбера:", "Barberni tanlang:"),
            reply_markup=kb
        )
    await callback.answer()


@client_barber_selection.callback_query(F.data == "open_filter")
async def open_filter(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == tg_user_id))).scalar_one_or_none()
        lang = getattr(user, "lang", "ru") if user else "ru"

        regions = (await session.execute(select(Region).order_by(Region.id))).scalars().all()
        if not regions:
            await callback.answer(
                _t(lang, "❌ Регионов не найдено.", "❌ Regionlar topilmadi."),
                show_alert=True
            )
            return

        await state.update_data(selected_region_id=None, selected_city_id=None)
        await callback.message.edit_text(
            _t(lang, "Выберите регион:", "Regionni tanlang:"),
            reply_markup=create_regions_keyboard(regions, lang)
        )

    await callback.answer()


@client_barber_selection.callback_query(F.data.startswith("choose_region:"))
async def handle_choose_region(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == tg_user_id))).scalar_one_or_none()
        lang = getattr(user, "lang", "ru") if user else "ru"

        region_id = int(callback.data.split(":")[1])
        cities = (await session.execute(
            select(City).where(City.region_id == region_id).order_by(City.id)
        )).scalars().all()

        if not cities:
            await callback.answer(
                _t(lang, "❌ В этом регионе нет городов.", "❌ Bu regoinda shahar yo‘q."),
                show_alert=True
            )
            return

        await state.update_data(selected_region_id=region_id, selected_city_id=None)
        await callback.message.edit_text(
            _t(lang, "Выберите город:", "Shaharni tanlang:"),
            reply_markup=create_cities_keyboard(cities, lang)
        )

    await callback.answer()


@client_barber_selection.callback_query(F.data.startswith("choose_city:"))
async def handle_choose_city(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == tg_user_id))).scalar_one_or_none()
        lang = getattr(user, "lang", "ru") if user else "ru"

        city_id = int(callback.data.split(":")[1])
        await state.update_data(selected_city_id=city_id)

        # Count for pagination in this city
        total_q = select(Barber.id).join(User, Barber.user_id == User.id).where(User.city_id == city_id)
        total = (await session.execute(total_q)).all()
        total_count = len(total)
        total_pages = max(1, ceil(total_count / PAGE_SIZE))

        page = 1
        await state.update_data(barbers_page=page)

        # Fetch current page (columns only)
        stmt = (
            select(Barber.id, Barber.score, User.name, User.surname)
            .join(User, Barber.user_id == User.id)
            .where(User.city_id == city_id)
            .order_by(desc(Barber.score))
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
        )
        rows = (await session.execute(stmt)).all()

        if not rows:
            await callback.message.edit_text(
                _t(lang, "😔 В этом городе пока нет барберов.", "😔 Bu shaharda hozircha barber yo‘q."),
                reply_markup=create_back_to_cities_keyboard(lang)
            )
            await callback.answer()
            return

        kb = make_barbers_keyboard_rows(rows, lang, page, total_pages, include_filter_button=False)
        # Append a "back to cities" row
        merged_rows = kb.inline_keyboard + create_back_to_cities_keyboard(lang).inline_keyboard

        await callback.message.edit_text(
            _t(lang, "Выберите барбера:", "Barberni tanlang:"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=merged_rows)
        )

    await callback.answer()


@client_barber_selection.callback_query(F.data == "back:regions")
async def back_to_regions(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == tg_user_id))).scalar_one_or_none()
        lang = getattr(user, "lang", "ru") if user else "ru"

        regions = (await session.execute(select(Region).order_by(Region.id))).scalars().all()

        await state.update_data(selected_region_id=None, selected_city_id=None)
        await callback.message.edit_text(
            _t(lang, "Выберите регион:", "Regionni tanlang:"),
            reply_markup=create_regions_keyboard(regions, lang)
        )

    await callback.answer()


@client_barber_selection.callback_query(F.data == "back:cities")
async def back_to_cities(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == tg_user_id))).scalar_one_or_none()
        lang = getattr(user, "lang", "ru") if user else "ru"

        data = await state.get_data()
        region_id = data.get("selected_region_id")

        if not region_id:
            # fallback to regions
            regions = (await session.execute(select(Region).order_by(Region.id))).scalars().all()
            await callback.message.edit_text(
                _t(lang, "Выберите регион:", "Regionni tanlang:"),
                reply_markup=create_regions_keyboard(regions, lang)
            )
            await callback.answer()
            return

        cities = (await session.execute(
            select(City).where(City.region_id == region_id).order_by(City.id)
        )).scalars().all()

        await callback.message.edit_text(
            _t(lang, "Выберите город:", "Shaharni tanlang:"),
            reply_markup=create_cities_keyboard(cities, lang)
        )

    await callback.answer()


@client_barber_selection.callback_query(F.data == "back:root")
async def back_root(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == tg_user_id))).scalar_one_or_none()
        lang = getattr(user, "lang", "ru") if user else "ru"

        # Use user's city if available
        if not user or not user.region_id or not user.city_id:
            regions = (await session.execute(select(Region).order_by(Region.id))).scalars().all()
            await callback.message.edit_text(
                _t(lang, "Выберите регион:", "Regionni tanlang:"),
                reply_markup=create_regions_keyboard(regions, lang)
            )
            await callback.answer()
            return

        city_id = user.city_id

        # Reset selected city in state to user's city context
        await state.update_data(selected_city_id=None)

        # Count for pagination
        total_q = select(Barber.id).join(User, Barber.user_id == User.id).where(User.city_id == city_id)
        total = (await session.execute(total_q)).all()
        total_count = len(total)
        total_pages = max(1, ceil(total_count / PAGE_SIZE))

        page = 1
        await state.update_data(barbers_page=page)

        # Fetch first page (columns only)
        stmt = (
            select(Barber.id, Barber.score, User.name, User.surname)
            .join(User, Barber.user_id == User.id)
            .where(User.city_id == city_id)
            .order_by(desc(Barber.score))
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
        )
        rows = (await session.execute(stmt)).all()

        if not rows:
            regions = (await session.execute(select(Region).order_by(Region.id))).scalars().all()
            await callback.message.edit_text(
                _t(lang, "Выберите регион:", "Regionni tanlang:"),
                reply_markup=create_regions_keyboard(regions, lang)
            )
            await callback.answer()
            return

        kb = make_barbers_keyboard_rows(rows, lang, page, total_pages, include_filter_button=True)
        await callback.message.edit_text(
            _t(lang, "Выберите барбера:", "Barberni tanlang:"),
            reply_markup=kb
        )

    await callback.answer()


@client_barber_selection.callback_query(F.data.startswith("select_barber:"))
async def handle_barber_selection(callback: CallbackQuery, state: FSMContext):
    barber_id = int(callback.data.split(":")[1])
    redis_pool = callback.bot.redis

    async with AsyncSessionLocal() as session:
        # Load barber (with linked User)
        barber_res = await session.execute(select(Barber).where(Barber.id == barber_id))
        barber = barber_res.scalar_one_or_none()

        # Load current user and client
        user_res = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user_res.scalar_one_or_none()

        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            return

        client_res = await session.execute(select(Client).where(Client.user_id == user.id).limit(1))
        client = client_res.scalar_one_or_none()

        if not barber:
            text = "Barber topilmadi." if (user.lang or "uz") == "uz" else "Барбер не найден."
            await callback.answer(text, show_alert=True)
            return

        if not client:
            await callback.answer("❌ Клиент не найден.", show_alert=True)
            return

        # Persist selection

        client.selected_barber = barber_id
        await session.commit()
        # Extract fields after write
        barber_name = barber.user.name if barber.user else ""
        barber_surname = barber.user.surname if barber.user else ""
        barber_score = barber.score or "—"
        lang = user.lang or "ru"

    # Redis + reply (outside DB session)
    await redis_pool.set(f"user:{user.telegram_id}:last_action", "barber_profile")

    text = "Siz tanlagan barber:" if lang == "uz" else "Вы выбрали барбера:"
    await callback.message.answer(
        f"{text} {barber_name} {barber_surname} ⭐ {barber_score}",
        reply_markup=barber_menu(lang),
    )
    await callback.answer()
