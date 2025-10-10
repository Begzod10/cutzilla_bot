from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, time
from app.states import BookingState, ChangeLocation
from app.user.models import User
from app.barber.models import (
    Barber, BarberService, BarberSchedule, BarberScheduleDetail
)
from app.service.models import Service
from app.client.models import Client, ClientRequest, ClientRequestService
from .keyboards import build_barber_services_kb, client_request_keyboard, format_barber_schedule_days
from .utils import get_region_city_multilang, find_free_slots
from app.region.models import Country, Region, City

# your async session factory
from app.db import AsyncSessionLocal  # ensure this import path is correct
from .callback_data import SchedPickSlotCBClient

client_request_router = Router()


@client_request_router.callback_query(SchedPickSlotCBClient.filter())
async def on_client_slot_picked(callback: CallbackQuery, callback_data: SchedPickSlotCBClient, state: FSMContext):
    lang = (await state.get_data()).get("lang", "uz")
    picked_day = callback_data.day  # "YYYY-MM-DD"
    picked_hm = callback_data.hm  # "HHMM" -> e.g., "1530"

    # Normalize and store chosen time/day in redis (or state)
    redis = callback.bot.redis
    await redis.set(f"user:{callback.from_user.id}:picked_day", picked_day)
    await redis.set(f"user:{callback.from_user.id}:picked_hm", picked_hm)

    # Reset selected services (fresh picking after time)
    await state.update_data(selected_services=[])

    # Load services for the selected barber
    async with AsyncSessionLocal() as session:
        tg_user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()

        client = (
            await session.execute(
                select(Client).where(Client.user_id == (tg_user.id if tg_user else None))
            )
        ).scalar_one_or_none()

        if not client or not client.selected_barber:
            msg = "❌ Ustani tanlang." if lang == "uz" else "❌ Выберите барбера."
            await callback.message.answer(msg)
            return

        barber_services = (
            await session.execute(
                select(BarberService)
                .where(
                    BarberService.barber_id == client.selected_barber,
                    BarberService.price != 0,
                    BarberService.duration.is_not(None),
                    BarberService.is_active.is_(True),
                )
                .order_by(BarberService.service_id)
            )
        ).scalars().all()

    if not barber_services:
        msg = "❌ Xizmatlar topilmadi." if lang == "uz" else "❌ Услуги не найдены."
        await callback.message.answer(msg)
        return

    kb = build_barber_services_kb(barber_services, lang, selected_ids=[])
    # Header shows selected date/time
    hhmm = f"{picked_hm[:2]}:{picked_hm[2:]}"
    day_human = datetime.strptime(picked_day, "%Y-%m-%d").strftime("%d.%m.%Y")
    text = (
        f"📅 {day_human} • ⏰ {hhmm}\n\n👇 Xizmatlarni tanlang:"
        if lang == "uz"
        else f"📅 {day_human} • ⏰ {hhmm}\n\n👇 Выберите услугу:"
    )

    # Replace current message safely
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)

    await callback.answer()


@client_request_router.callback_query(F.data.startswith("choose_service_client:"))
async def toggle_service_callback(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    lang = data.get("lang", "uz")
    selected_ids = data.get("selected_services", [])

    # toggle
    if service_id in selected_ids:
        selected_ids.remove(service_id)
    else:
        selected_ids.append(service_id)

    await state.update_data(selected_services=selected_ids)

    async with AsyncSessionLocal() as session:
        tg_user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        client = (
            await session.execute(
                select(Client).where(Client.user_id == (tg_user.id if tg_user else None))
            )
        ).scalar_one_or_none()

        barber_services = []
        if client and client.selected_barber:
            barber_services = (
                await session.execute(
                    select(BarberService)
                    .where(
                        BarberService.barber_id == client.selected_barber,
                        BarberService.price != 0,
                        BarberService.duration.is_not(None),
                    )
                    .order_by(BarberService.service_id)
                )
            ).scalars().all()

    kb = build_barber_services_kb(barber_services, lang, selected_ids)
    text = "👇 Xizmatlarni tanlang:" if lang == "uz" else "👇 Выберите услугу:"
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@client_request_router.callback_query(F.data == "confirm_services")
async def confirm_services_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = data.get("selected_services", [])
    lang = data.get("lang", "uz")

    if not selected_ids:
        msg = "❌ Hech qanday xizmat tanlanmadi." if lang == "uz" else "❌ Услуги не выбраны."
        await callback.answer(msg, show_alert=True)
        return

    redis = callback.bot.redis
    picked_day = await redis.get(f"user:{callback.from_user.id}:picked_day")  # "YYYY-MM-DD"
    picked_hm = await redis.get(f"user:{callback.from_user.id}:picked_hm")  # "HHMM"

    if not picked_day or not picked_hm:
        # Safety: user somehow reached here without picking a time
        msg = (
            "❌ Avval bo'sh vaqtni tanlang."
            if lang == "uz" else "❌ Сначала выберите свободное время."
        )
        await callback.answer(msg, show_alert=True)
        return

    # Parse start datetime from stored slot
    start_time = datetime.strptime(picked_hm, "%H%M").time()
    day_date = datetime.strptime(picked_day, "%Y-%m-%d").date()
    start_dt = datetime.combine(day_date, start_time)

    async with AsyncSessionLocal() as session:
        # user & client
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await callback.message.answer("❌ User not found.")
            return

        client = (
            await session.execute(
                select(Client).where(Client.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not client or not client.selected_barber:
            await callback.message.answer("❌ Barber not selected.")
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.id == client.selected_barber)
            )
        ).scalar_one_or_none()
        if not barber or not barber.start_time or not barber.end_time:
            text = "❌ Barberning ish vaqti topilmadi." if lang == "uz" else "❌ Рабочее время барбера не найдено."
            await callback.message.answer(text)
            return

        # schedule (must match user's last selected schedule)
        barber_schedule = (
            await session.execute(
                select(BarberSchedule).where(BarberSchedule.id == client.selected_schedule_id)
            )
        ).scalar_one_or_none()
        if not barber_schedule:
            await callback.message.answer("❌ Jadval topilmadi." if lang == "uz" else "❌ Расписание не найдено.")
            return

        # Ensure slot day equals schedule day
        sched_day = barber_schedule.day.date() if hasattr(barber_schedule.day, "date") else barber_schedule.day
        if sched_day != day_date:
            msg = (
                f"❌ Noto‘g‘ri sana tanlandi. Jadval kuni: {sched_day.strftime('%d.%m.%Y')}, tanlangan: {day_date.strftime('%d.%m.%Y')}"
                if lang == "uz"
                else f"❌ Выбрана неверная дата. День расписания: {sched_day.strftime('%d.%m.%Y')}, выбранная: {day_date.strftime('%d.%m.%Y')}"
            )
            await callback.message.answer(msg)
            return

        # Not in the past (if schedule is today)
        now = datetime.now()
        if day_date == now.date() and start_dt <= now:
            msg = (
                "❌ O‘tgan vaqtni tanlab bo‘lmaydi, iltimos hozirgi vaqtdan keyinroq vaqtni tanlang."
                if lang == "uz"
                else "❌ Нельзя выбрать прошедшее время, укажите время позже текущего."
            )
            await callback.message.answer(msg)
            return

        # Load selected services and compute totals
        services = (
            await session.execute(
                select(BarberService).where(BarberService.id.in_(selected_ids))
            )
        ).scalars().all()
        total_duration = sum(s.duration or 0 for s in services)
        total_price = sum(s.price or 0 for s in services)

        end_dt = start_dt + timedelta(minutes=total_duration)

        # Working hours boundaries
        work_start = datetime.combine(day_date, barber.start_time.time())
        work_end = datetime.combine(day_date, barber.end_time.time())

        # Must start >= work_start and end <= work_end (23:00 is finish, not accepted)
        if not (start_dt >= work_start and end_dt <= work_end):
            msg = (
                f"❌ Tanlangan vaqt ish vaqtidan tashqarida.\nIsh vaqti: {work_start.strftime('%H:%M')} – {work_end.strftime('%H:%M')}"
                if lang == "uz"
                else f"❌ Выбранное время вне рабочего графика.\nГрафик: {work_start.strftime('%H:%M')} – {work_end.strftime('%H:%M')}"
            )
            await callback.message.answer(msg)
            return

        # Check overlap within this schedule
        conflict = (
            await session.execute(
                select(ClientRequest).where(
                    ClientRequest.barber_schedule_id == barber_schedule.id,
                    ClientRequest.status != "deny",
                    ClientRequest.client_id != client.id,
                    and_(ClientRequest.from_time < end_dt, ClientRequest.to_time > start_dt)
                ).limit(1)
            )
        ).scalar_one_or_none()

        if conflict:
            # Show busy ranges and stop
            client_requests = (
                await session.execute(
                    select(ClientRequest).where(
                        ClientRequest.barber_schedule_id == barber_schedule.id,
                        ClientRequest.client_id != client.id
                    )
                )
            ).scalars().all()

            await callback.message.answer("❌ Bu vaqt band!" if lang == "uz" else "❌ Это время уже занято!")
            if client_requests:
                times_text = "\n".join(
                    f"{cr.from_time.strftime('%H:%M')} - {cr.to_time.strftime('%H:%M')}"
                    for cr in client_requests if cr.from_time and cr.to_time
                )
                msg2 = (
                    f"📅 {sched_day.strftime('%d.%m.%Y')}\n⛔ Band vaqtlar:\n{times_text}"
                    if lang == "uz"
                    else f"📅 {sched_day.strftime('%d.%m.%Y')}\n⛔ Занятые времена:\n{times_text}"
                )
                await callback.message.answer(msg2)
            return

        # Prevent duplicate future request for same day/schedule
        existing_for_today = (
            await session.execute(
                select(ClientRequest).where(
                    ClientRequest.barber_schedule_id == barber_schedule.id,
                    ClientRequest.barber_id == barber.id,
                    ClientRequest.client_id == client.id,
                    ClientRequest.date >= datetime.combine(day_date, time.min),
                    ClientRequest.date <= datetime.combine(day_date, time.max),
                    ClientRequest.from_time > now,
                ).limit(1)
            )
        ).scalar_one_or_none()

        # if existing_for_today:
        #     text = "⚠️ Siz allaqachon so'rov yubordingiz" if lang == "uz" else "⚠️ Вы уже отправляли заявку"
        #     await callback.message.answer(text)
        #     await state.clear()
        #     return

        # Create request
        client_request_add = ClientRequest(
            client_id=client.id,
            barber_id=barber.id,
            barber_schedule_id=barber_schedule.id,
            date=start_dt,
            from_time=start_dt,
            to_time=end_dt,
        )
        session.add(client_request_add)
        await session.flush()

        # Add service lines
        for s in services:
            exists = (
                await session.execute(
                    select(ClientRequestService).where(
                        ClientRequestService.client_request_id == client_request_add.id,
                        ClientRequestService.barber_service_id == s.id,
                    ).limit(1)
                )
            ).scalar_one_or_none()
            if not exists:
                session.add(ClientRequestService(
                    client_request_id=client_request_add.id,
                    barber_service_id=s.id,
                    duration=s.duration
                ))

        await session.commit()
        # --- Notify the barber that a new request arrived (UZ/RU) ---
        # 1) Load barber's user to get telegram_id and language
        barber_user = (
            await session.execute(
                select(User).where(User.id == barber.user_id)
            )
        ).scalar_one_or_none()

        client_user = (
            await session.execute(
                select(User).where(User.id == client.user_id)
            )
        ).scalar_one_or_none()

        # Safety checks
        if barber_user and getattr(barber_user, "telegram_id", None):
            # 2) Compose service lines in both languages
            sv_lines_uz, sv_lines_ru = [], []
            for s in services:
                svc = s  # BarberService
                base = getattr(svc, "service", None)
                name_uz = base.name_uz if base else "—"
                name_ru = base.name_ru if base else "—"
                price = svc.price or 0
                dur = svc.duration or 0
                sv_lines_uz.append(f"{name_uz}: {price} so'm, {dur} min")
                sv_lines_ru.append(f"{name_ru}: {price} сум, {dur} мин")

            services_uz = "\n".join(sv_lines_uz) or "—"
            services_ru = "\n".join(sv_lines_ru) or "—"

            # 3) Build UZ/RU messages
            client_fio = f"{client_user.name or ''} {client_user.surname or ''}".strip() if client_user else "—"
            client_tg_id = getattr(client_user, "telegram_id", None)

            msg_uz = (
                "🆕 Yangi so'rov!\n"
                f"👤 Mijoz: {client_fio}\n"
                f"📆 Sana: {day_date.strftime('%d.%m.%Y')}\n"
                f"🕒 Vaqt: {start_dt.strftime('%H:%M')} – {end_dt.strftime('%H:%M')}\n"
                f"🛠️ Xizmatlar:\n{services_uz}\n"
                f"⏱️ Umumiy davomiylik: {total_duration} min\n"
                f"💰 Umumiy narx: {total_price} so'm\n"
                f"💬 Izoh: {client_request_add.comment or '-'}\n\n"
                "Iltimos, so'rovni tasdiqlang yoki rad eting:"
            )

            msg_ru = (
                "🆕 Новая заявка!\n"
                f"👤 Клиент: {client_fio}\n"
                f"📆 Дата: {day_date.strftime('%d.%m.%Y')}\n"
                f"🕒 Время: {start_dt.strftime('%H:%M')} – {end_dt.strftime('%H:%M')}\n"
                f"🛠️ Услуги:\n{services_ru}\n"
                f"⏱️ Общая продолжительность: {total_duration} мин\n"
                f"💰 Общая сумма: {total_price} сум\n"
                f"💬 Комментарий: {client_request_add.comment or '-'}\n\n"
                "Пожалуйста, подтвердите или отклоните заявку:"
            )

            # 4) Choose barber language (default UZ)
            barber_lang = getattr(barber_user, "lang", "uz") or "uz"
            msg_for_barber = msg_ru if barber_lang == "ru" else msg_uz

            # 5) Inline keyboard: Accept / Deny (+ link to client's Telegram)
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            accept_text = "✅ Подтвердить" if barber_lang == "ru" else "✅ Tasdiqlash"
            deny_text = "❌ Отклонить" if barber_lang == "ru" else "❌ Rad etish"
            view_client_text = "👤 Профиль клиента" if barber_lang == "ru" else "👤 Mijoz profili"

            kb_rows = [[
                InlineKeyboardButton(text=accept_text, callback_data=f"req:{client_request_add.id}:accept"),
                InlineKeyboardButton(text=deny_text, callback_data=f"req:{client_request_add.id}:deny"),
            ]]

            # Optional: deep link to client's Telegram profile if we have their telegram_id
            if client_tg_id:
                kb_rows.append([
                    InlineKeyboardButton(text=view_client_text, url=f"tg://user?id={client_tg_id}")
                ])

            barber_kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

            # 6) Send the message to the barber
            try:
                await callback.bot.send_message(
                    chat_id=barber_user.telegram_id,
                    text=msg_for_barber,
                    reply_markup=barber_kb
                )
            except Exception as e:
                # You might want to log this
                print("Failed to notify barber:", e)

    # Feedback
    msg = (
        f"✅ Siz tanlagan vaqt: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}.\n"
        f"🕒 Umumiy davomiylik: {total_duration} daqiqa\n"
        f"💰 Umumiy narx: {total_price} so'm\n"
        f"Arizangiz qabul qilinishini kuting."
        if lang == "uz"
        else f"✅ Вы выбрали время: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}.\n"
             f"🕒 Общая продолжительность: {total_duration} мин.\n"
             f"💰 Общая сумма: {total_price} сум\n"
             f"Ожидайте подтверждения заявки."
    )
    await callback.message.answer(msg)

    # cleanup
    await state.clear()
    await redis.delete(f"user:{callback.from_user.id}:picked_day")
    await redis.delete(f"user:{callback.from_user.id}:picked_hm")
