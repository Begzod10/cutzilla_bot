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
from .keyboards import build_barber_services_self_kb
from app.region.models import Country, Region, City

# your async session factory
from app.db import AsyncSessionLocal  # ensure this import path is correct
from app.barber.schedule.callback_data import SchedPickSlotCBForBarber

barber_request_router = Router()


@barber_request_router.callback_query(SchedPickSlotCBForBarber.filter())
async def on_client_slot_picked(callback: CallbackQuery, callback_data: SchedPickSlotCBForBarber, state: FSMContext):
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

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == (tg_user.id if tg_user else None))
            )
        ).scalar_one_or_none()

        barber_services = (
            await session.execute(
                select(BarberService)
                .where(
                    BarberService.barber_id == barber.id,
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

    kb = build_barber_services_self_kb(barber_services, lang, selected_ids=[])
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


@barber_request_router.callback_query(F.data.startswith("choose_service_barber:"))
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

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == (tg_user.id if tg_user else None))
            )
        ).scalar_one_or_none()

        barber_services = []

        barber_services = (
            await session.execute(
                select(BarberService)
                .where(
                    BarberService.barber_id == barber.id,
                    BarberService.price != 0,
                    BarberService.duration.is_not(None),
                )
                .order_by(BarberService.service_id)
            )
        ).scalars().all()

    kb = build_barber_services_self_kb(barber_services, lang, selected_ids)
    text = "👇 Xizmatlarni tanlang:" if lang == "uz" else "👇 Выберите услугу:"
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@barber_request_router.callback_query(F.data == "barber_confirm_services")
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

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not barber or not barber.start_time or not barber.end_time:
            text = "❌ Barberning ish vaqti topilmadi." if lang == "uz" else "❌ Рабочее время барбера не найдено."
            await callback.message.answer(text)
            return

        # schedule (must match user's last selected schedule)
        barber_schedule = (
            await session.execute(
                select(BarberSchedule).where(BarberSchedule.id == barber.selected_schedule_id)
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
                    # ClientRequest.client_id != client.id,
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
                        # ClientRequest.client_id != client.id
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
                    # ClientRequest.client_id == client.id,
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
            # client_id=client.id,
            barber_id=barber.id,
            barber_schedule_id=barber_schedule.id,
            date=start_dt,
            from_time=start_dt,
            to_time=end_dt,
            status="accept",
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
