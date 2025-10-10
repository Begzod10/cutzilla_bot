from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, time
from .callback_data import SchedPickSlotCBClientEdit
from app.states import BookingState
from app.user.models import User
from app.barber.models import (
    Barber, BarberService, BarberSchedule
)

from app.client.models import Client, ClientRequest, ClientRequestService
from .keyboards import (
    client_request_keyboard, edit_request_keyboard,
    build_barber_edit_services_kb, barber_menu, kb_day_slots_by_sched_client_to_change
)

# ✅ your async session factory
from app.db import AsyncSessionLocal  # ensure the import path is correct

client_request_info_router = Router()


@client_request_info_router.message(F.text.in_(["📋 So‘rovlarim", '📋 Мои заявки']))
async def my_requests(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        tg_user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not tg_user:
            await message.answer(
                "❌ Пользователь не найден." if getattr(message.from_user, "lang",
                                                       "uz") != "uz" else "❌ Foydalanuvchi topilmadi."
            )
            return

        client = (
            await session.execute(
                select(Client).where(Client.user_id == tg_user.id)
            )
        ).scalar_one_or_none()
        if not client:
            await message.answer("❌ Клиент не найден." if tg_user.lang != "uz" else "❌ Klient topilmadi.")
            return

        # safe range for "today and after" if ClientRequest.date is TIMESTAMP
        today = datetime.now().date()
        start_of_today = datetime.combine(today, time.min)

        client_requests = (
            await session.execute(
                select(ClientRequest)
                .where(
                    ClientRequest.client_id == client.id,
                    ClientRequest.date >= start_of_today,
                    ClientRequest.status == "pending",
                )
                .order_by(ClientRequest.date.desc())
            )
        ).scalars().all()

        lang = tg_user.lang
        if not client_requests:
            msg = "📋 Sizda hali so'rovlar yo'q." if lang == "uz" else "📋 У вас пока нет заявок."
            await message.answer(msg)
            return

        for cr in client_requests:
            barber = (
                await session.execute(
                    select(Barber)
                    .options(selectinload(Barber.user))
                    .where(Barber.id == cr.barber_id)
                )
            ).scalar_one_or_none()

            cr_services = (
                await session.execute(
                    select(ClientRequestService)
                    .where(ClientRequestService.client_request_id == cr.id)
                    .order_by(ClientRequestService.barber_service_id)
                )
            ).scalars().all()

            # Build services text and total price
            services_text = ""
            total_price = 0
            for crs in cr_services:
                service = (
                    await session.execute(
                        select(BarberService)
                        .options(selectinload(BarberService.service))
                        .where(BarberService.id == crs.barber_service_id)
                    )
                ).scalar_one_or_none()
                if not service:
                    continue
                total_price += service.price or 0
                if lang == "uz":
                    services_text += f"\n   ✂️ {service.service.name_uz} ({service.price} so'm, {service.duration} daqiqa)"
                else:
                    services_text += f"\n   ✂️ {service.service.name_ru} ({service.price} сум, {service.duration} мин.)"

            if lang == "uz":
                text = (
                    f"✂️ Barber: {barber.user.name if barber and barber.user else ''} {barber.user.surname if barber and barber.user else ''}\n"
                    f"📅 Sana: {cr.date.strftime('%d.%m.%Y')}\n"
                    f"⏰ Vaqt: {cr.from_time.strftime('%H:%M')} - {cr.to_time.strftime('%H:%M')}\n"
                    f"📌 Holat: {'✅ Tasdiqlangan' if cr.status == 'accept' else '❌ Rad etilgan' if cr.status == 'deny' else '⏳ Kutilmoqda'}\n"
                    f"🧾 Xizmatlar:{services_text}\n"
                    f"💰 Umumiy narx: {total_price} so'm"
                )
            else:
                text = (
                    f"✂️ Барбер: {barber.user.name if barber and barber.user else ''} {barber.user.surname if barber and barber.user else ''}\n"
                    f"📅 Дата: {cr.date.strftime('%d.%m.%Y')}\n"
                    f"⏰ Время: {cr.from_time.strftime('%H:%M')} - {cr.to_time.strftime('%H:%M')}\n"
                    f"📌 Статус: {'✅ Подтверждено' if cr.status == 'accept' else '❌ Отклонено' if cr.status == 'deny' else '⏳ В ожидании'}\n"
                    f"🧾 Услуги:{services_text}\n"
                    f"💰 Общая сумма: {total_price} сум"
                )

            await message.answer(text, reply_markup=client_request_keyboard(cr, lang))


@client_request_info_router.callback_query(F.data.startswith("req_feedback:"))
async def start_feedback(callback: CallbackQuery, state: FSMContext):
    request_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        client_request = (
            await session.execute(
                select(ClientRequest).where(ClientRequest.id == request_id)
            )
        ).scalar_one_or_none()
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()

        if not client_request or not user:
            await callback.answer("❌ Xatolik yuz berdi", show_alert=True)
            return

    text = "📝 Endi fikringizni kiriting:" if user.lang == "uz" else "📝 Оставьте свой отзыв:"
    await callback.message.answer(text)

    await state.update_data(request_id=request_id)
    await state.set_state(BookingState.waiting_for_feedback)
    await callback.answer()


@client_request_info_router.message(BookingState.waiting_for_feedback)
async def save_feedback(message: Message, state: FSMContext):
    data = await state.get_data()
    request_id = data.get("request_id")

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        client_request = (
            await session.execute(
                select(ClientRequest).where(ClientRequest.id == request_id)
            )
        ).scalar_one_or_none()

        if not client_request or not user:
            await message.answer("❌ Xatolik yuz berdi." if (user and user.lang == "uz") else "❌ Произошла ошибка.")
            await state.clear()
            return

        client_request.comment = message.text
        await session.commit()

    await state.clear()
    text = "✅ Fikringiz muvaffaqiyatli yuborildi." if user.lang == "uz" else "✅ Ваш отзыв успешно отправлен."
    await message.answer(text)


@client_request_info_router.callback_query(F.data.startswith("req_details:"))
async def show_request_details(callback: CallbackQuery, state: FSMContext):
    request_id = int(callback.data.split(":")[1])
    redis_pool = callback.bot.redis

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        client_request = (
            await session.execute(
                select(ClientRequest).where(ClientRequest.id == request_id)
            )
        ).scalar_one_or_none()
        client = (
            await session.execute(
                select(Client).where(Client.user_id == (user.id if user else None))
            )
        ).scalar_one_or_none()

        if not client_request or not user or not client:
            await callback.answer(
                "❌ Xatolik yuz berdi." if user and user.lang == "uz" else "❌ Произошла ошибка.",
                show_alert=True
            )
            return

        client.selected_request_id = request_id
        await session.commit()

        await state.update_data(request_id=request_id)
        await redis_pool.set(f"user:{user.telegram_id}:last_action", "request_profile")

    text = "✏️ So‘rovni tahrirlash:" if user.lang == "uz" else "✏️ Редактировать заявку:"
    await callback.message.answer(text, reply_markup=edit_request_keyboard(user.lang))
    await callback.answer()


@client_request_info_router.message(F.text.in_(["💇 Xizmatlarni o‘zgartirish", '💇 Изменить услуги']))
async def edit_services(message: Message, state: FSMContext):
    user = message.from_user
    today = datetime.now().date()

    async with AsyncSessionLocal() as session:
        tg_user = (
            await session.execute(
                select(User).where(User.telegram_id == user.id)
            )
        ).scalar_one_or_none()
        if not tg_user:
            await message.answer(
                "❌ Foydalanuvchi topilmadi." if getattr(tg_user, "lang", "uz") == "uz" else "❌ Пользователь не найден."
            )
            return

        lang = tg_user.lang
        client = (
            await session.execute(
                select(Client).where(Client.user_id == tg_user.id)
            )
        ).scalar_one_or_none()
        barber = (
            await session.execute(
                select(Barber).where(Barber.id == client.selected_barber)
            )
        ).scalar_one_or_none()
        client_request = (
            await session.execute(
                select(ClientRequest).where(ClientRequest.id == client.selected_request_id)
            )
        ).scalar_one_or_none()

        if not client_request or client_request.date.date() < today:
            text = "❌ Siz eski so'rovdan foydalanmoqdasiz" if lang == "uz" else "❌ Вы используете старое заявление"
            await message.answer(text)

            start_of_today = datetime.combine(today, time.min)
            client_requests = (
                await session.execute(
                    select(ClientRequest)
                    .where(
                        ClientRequest.client_id == client.id,
                        ClientRequest.date >= start_of_today,
                    )
                    .order_by(ClientRequest.date.desc())
                )
            ).scalars().all()

            if not client_requests:
                await message.answer("📋 Sizda hali so'rovlar yo'q." if lang == "uz" else "📋 У вас пока нет заявок.")
                return

            for cr in client_requests:
                br = (
                    await session.execute(
                        select(Barber).options(selectinload(Barber.user)).where(Barber.id == cr.barber_id)
                    )
                ).scalar_one_or_none()

                cr_services = (
                    await session.execute(
                        select(ClientRequestService)
                        .where(ClientRequestService.client_request_id == cr.id)
                        .order_by(ClientRequestService.barber_service_id)
                    )
                ).scalars().all()

                services_text = ""
                for s in cr_services:
                    sv = (
                        await session.execute(
                            select(BarberService)
                            .options(selectinload(BarberService.service))
                            .where(BarberService.id == s.barber_service_id)
                        )
                    ).scalar_one_or_none()
                    if not sv:
                        continue
                    if lang == "uz":
                        services_text += f"\n   ✂️ {sv.service.name_uz} ({sv.price} so'm, {sv.duration} daqiqa)"
                    else:
                        services_text += f"\n   ✂️ {sv.service.name_ru} ({sv.price} сум, {sv.duration} мин.)"

                if lang == "uz":
                    text = (
                        f"✂️ Barber: {br.user.name if br and br.user else ''} {br.user.surname if br and br.user else ''}\n"
                        f"📅 Sana: {cr.date.strftime('%d.%m.%Y')}\n"
                        f"⏰ Vaqt: {cr.from_time.strftime('%H:%M')} - {cr.to_time.strftime('%H:%M')}\n"
                        f"📌 Holat: {'✅ Tasdiqlangan' if cr.status else '⏳ Kutilmoqda'}\n"
                        f"🧾 Xizmatlar:{services_text}"
                    )
                else:
                    text = (
                        f"✂️ Барбер: {br.user.name if br and br.user else ''} {br.user.surname if br and br.user else ''}\n"
                        f"📅 Дата: {cr.date.strftime('%d.%m.%Y')}\n"
                        f"⏰ Время: {cr.from_time.strftime('%H:%M')} - {cr.to_time.strftime('%H:%M')}\n"
                        f"📌 Статус: {'✅ Подтверждено' if cr.status else '⏳ В ожидании'}\n"
                        f"🧾 Услуги:{services_text}"
                    )
                await message.answer(text, reply_markup=client_request_keyboard(cr, lang))
            return

        # Existing request → preselect its services
        cr_services = (
            await session.execute(
                select(ClientRequestService).where(ClientRequestService.client_request_id == client_request.id)
            )
        ).scalars().all()
        selected_ids = [s.barber_service_id for s in cr_services]
        await state.update_data(selected_services=selected_ids)

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

    kb = build_barber_edit_services_kb(barber_services, lang, selected_ids)
    text = "👇 Xizmatlarni tanlang:" if lang == "uz" else "👇 Выберите услугу:"
    await message.answer(text, reply_markup=kb)


@client_request_info_router.callback_query(F.data.startswith("edit_choose_service_client:"))
async def toggle_service_callback(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected_ids = data.get("selected_services", [])

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
        lang = tg_user.lang
        client = (
            await session.execute(
                select(Client).where(Client.user_id == (tg_user.id if tg_user else None))
            )
        ).scalar_one_or_none()
        barber = (
            await session.execute(
                select(Barber).where(Barber.id == (client.selected_barber if client else None))
            )
        ).scalar_one_or_none()

        barber_services = []
        if barber:
            barber_services = (
                await session.execute(
                    select(BarberService)
                    .where(
                        BarberService.barber_id == barber.id,
                        BarberService.price != 0,
                        BarberService.duration.is_not(None)
                    )
                    .order_by(BarberService.service_id)
                )
            ).scalars().all()
    print(lang)
    kb = build_barber_edit_services_kb(barber_services, lang, selected_ids)
    text = "👇 Xizmatlarni tanlang:" if lang == "uz" else "👇 Выберите услугу:"
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@client_request_info_router.callback_query(F.data == "edit_confirm_services")
async def confirm_services_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = data.get("selected_services", [])
    lang = data.get("lang", "uz")

    if not selected_ids:
        msg = "❌ Hech qanday xizmat tanlanmadi." if lang == "uz" else "❌ Услуги не выбраны."
        await callback.answer(msg, show_alert=True)
        return

    redis_pool = callback.bot.redis

    async with AsyncSessionLocal() as session:
        user = (await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )).scalar_one_or_none()

        client = (await session.execute(
            select(Client).where(Client.user_id == (user.id if user else None))
        )).scalar_one_or_none()

        # Fetch chosen services with their linked base service for names
        services = (await session.execute(
            select(BarberService)
            .options(selectinload(BarberService.service))
            .where(BarberService.id.in_(selected_ids))
        )).scalars().all()

        await redis_pool.set(
            f"user:{callback.from_user.id}:selected_services",
            ",".join(map(str, selected_ids))
        )

        # Clear old services (use DELETE directly)
        await session.execute(
            ClientRequestService.__table__.delete().where(
                ClientRequestService.client_request_id == client.selected_request_id
            )
        )

        # Add new services
        for srv in services:
            session.add(ClientRequestService(
                client_request_id=client.selected_request_id,
                barber_service_id=srv.id
            ))

        # ⬇️ NEW: recompute total duration and update request end time
        total_duration = sum((srv.duration or 0) for srv in services)

        cr = (await session.execute(
            select(ClientRequest).where(ClientRequest.id == client.selected_request_id)
        )).scalar_one_or_none()

        end_dt_str = None  # for UI message
        if cr:
            if total_duration <= 0:
                # keep previous to_time as-is; you can also choose to null it
                pass
            else:
                # only adjust if start is set
                if cr.from_time:
                    cr.to_time = cr.from_time + timedelta(minutes=total_duration)
                    end_dt_str = cr.to_time.strftime("%H:%M")

            # (Optional) store total minutes/price on request if you track them
            # cr.total_minutes = total_duration
            # cr.total_price = sum((srv.price or 0) for srv in services)

        await session.commit()

    # Build UI text
    if lang == "uz":
        text = "✅ Siz tanlagan xizmatlar:\n\n" + "\n".join(
            [f"✂️ {s.service.name_uz} • {s.price} so'm • {s.duration} daqiqa" for s in services]
        )
        confirmation_text = "✅ Xizmatlar muvaffaqiyatli o'zgartirildi."
        if end_dt_str:
            confirmation_text += f" ⏱ Tugash vaqti: {end_dt_str}"
    else:
        text = "✅ Вы выбрали услуги:\n\n" + "\n".join(
            [f"✂️ {s.service.name_ru} • {s.price} сум • {s.duration} минут" for s in services]
        )
        confirmation_text = "✅ Услуги успешно изменены."
        if end_dt_str:
            confirmation_text += f" ⏱ Окончание: {end_dt_str}"

    await callback.message.edit_text(text)
    await callback.message.answer(confirmation_text)


@client_request_info_router.message(F.text.in_({"⏰ Vaqtni o‘zgartirish", "⏰ Изменить время"}))
async def change_time(message: Message):
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        user = (await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )).scalar_one_or_none()
        lang = getattr(user, "lang", "uz")

        client = (await session.execute(
            select(Client).where(Client.user_id == (user.id if user else None))
        )).scalar_one_or_none()

        if not client or not client.selected_schedule_id:
            await message.answer("❌ Jadval topilmadi." if lang == "uz" else "❌ Расписание не найдено.")
            return
        client_request = (
            await session.execute(
                select(ClientRequest).where(
                    ClientRequest.id == (client.selected_request_id if client else None)
                )
            )
        ).scalar_one_or_none()

        # build the inline keyboard with your function
        kb = await kb_day_slots_by_sched_client_to_change(
            session=session,
            barber_id=client_request.barber_id,
            sched_id=client_request.barber_schedule_id,
            slot_minutes=30,
        )

    txt = "🕒 Yangi vaqtni tanlang:" if lang == "uz" else "🕒 Выберите новое время:"
    await message.answer(txt, reply_markup=kb)


@client_request_info_router.callback_query(SchedPickSlotCBClientEdit.filter())
async def on_client_pick_slot(call: CallbackQuery, callback_data: SchedPickSlotCBClientEdit):
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        # --- entities ---
        user = (await session.execute(
            select(User).where(User.telegram_id == call.from_user.id)
        )).scalar_one_or_none()
        lang = getattr(user, "lang", "uz")

        client = (await session.execute(
            select(Client).where(Client.user_id == (user.id if user else None))
        )).scalar_one_or_none()

        if not client or not client.selected_schedule_id or not client.selected_request_id:
            await call.answer("❌ Kontekst topilmadi.", show_alert=True)
            return

        barber_schedule = (await session.execute(
            select(BarberSchedule).where(BarberSchedule.id == client.selected_schedule_id)
        )).scalar_one_or_none()
        if not barber_schedule or not barber_schedule.day:
            await call.answer("❌ Jadval topilmadi.", show_alert=True)
            return

        barber = (await session.execute(
            select(Barber).where(Barber.id == client.selected_barber)
        )).scalar_one_or_none()
        if not barber or not barber.start_time or not barber.end_time:
            await call.answer("❌ Barber ish vaqti topilmadi.", show_alert=True)
            return

        # --- parse chosen time from callback ---
        # callback_data.day: "YYYY-MM-DD"; callback_data.hm: "HHMM"
        try:
            sched_day = datetime.strptime(callback_data.day, "%Y-%m-%d").date()
            chosen_time = time(int(callback_data.hm[:2]), int(callback_data.hm[2:]))
        except Exception:
            await call.answer("❌ Noto‘g‘ri vaqt.", show_alert=True)
            return

        # KEEP same-day guard (optional; remove if not needed)
        if (barber_schedule.day.date() if hasattr(barber_schedule.day, "date") else barber_schedule.day) != sched_day:
            await call.answer(
                ("❌ Boshqa kun uchun tanlov." if lang == "uz" else "❌ Выбор для другого дня."),
                show_alert=True
            )
            return

        # --- compute total duration from selected services ---
        cr_services = (await session.execute(
            select(ClientRequestService)
            .options(selectinload(ClientRequestService.barber_service))
            .where(ClientRequestService.client_request_id == client.selected_request_id)
        )).scalars().all()
        total_duration = sum((s.barber_service.duration or 0) for s in cr_services if s.barber_service)

        if total_duration <= 0:
            await call.answer("❌ Avval xizmat(lar)ni tanlang.", show_alert=True) if lang == "uz" \
                else await call.answer("❌ Сначала выберите услугу(и).", show_alert=True)
            return

        start_dt = datetime.combine(sched_day, chosen_time)
        end_dt = start_dt + timedelta(minutes=total_duration)

        work_start = datetime.combine(sched_day, barber.start_time.time())
        work_end = datetime.combine(sched_day, barber.end_time.time())

        # hard bounds
        if start_dt < work_start:
            msg = (f"❌ Juda erta. Ish vaqti: {work_start:%H:%M}–{work_end:%H:%M}"
                   if lang == "uz" else f"❌ Слишком рано. Рабочее время: {work_start:%H:%M}–{work_end:%H:%M}")
            await call.answer(msg, show_alert=True)
            return

        if end_dt > work_end:
            latest = (work_end - timedelta(minutes=total_duration)).strftime("%H:%M")
            msg = (f"❌ Xizmat davomiyligi ish vaqtidan oshadi. Maksimal boshlanish: {latest}"
                   if lang == "uz" else f"❌ Длительность выходит за рабочее время. Максимальное начало: {latest}")
            await call.answer(msg, show_alert=True)
            return

        # no past today
        now = datetime.now()
        if sched_day == now.date() and start_dt <= now:
            await call.answer(
                "❌ O‘tgan vaqtni tanlab bo‘lmaydi." if lang == "uz" else "❌ Нельзя выбрать прошедшее время.",
                show_alert=True
            )
            return

        # conflicts: accepted requests on the same schedule, others only
        conflict = (await session.execute(
            select(ClientRequest)
            .where(
                ClientRequest.barber_schedule_id == barber_schedule.id,
                ClientRequest.status == "accept",
                ClientRequest.client_id != client.id,
                and_(ClientRequest.from_time < end_dt, ClientRequest.to_time > start_dt)
            )
            .limit(1)
        )).scalar_one_or_none()

        if conflict:
            await call.answer("❌ Bu vaqt band!" if lang == "uz" else "❌ Это время занято!", show_alert=True)
            return

        # --- update request ---
        client_request = (await session.execute(
            select(ClientRequest).where(ClientRequest.id == client.selected_request_id)
        )).scalar_one_or_none()

        if not client_request:
            await call.answer("❌ So‘rov topilmadi." if lang == "uz" else "❌ Заявление не найдено.", show_alert=True)
            return

        client_request.from_time = start_dt
        client_request.to_time = end_dt
        await session.commit()

    # UX: confirm & remove keyboard
    txt_ok = ("✅ Vaqt o‘zgartirildi: "
              f"{start_dt:%d.%m.%Y} {start_dt:%H:%M}–{end_dt:%H:%M}") if lang == "uz" else \
        ("✅ Время изменено: "
         f"{start_dt:%d.%m.%Y} {start_dt:%H:%M}–{end_dt:%H:%M}")
    try:
        await call.message.edit_reply_markup()  # drop old keyboard if possible
    except Exception:
        pass
    await call.answer(txt_ok, show_alert=True)


@client_request_info_router.message(F.text.in_(["❌ Bekor qilish", '❌ Отменить']))
async def cancel(message: Message, state: FSMContext):
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        # Load user, client, request
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

        client = (
            await session.execute(
                select(Client).where(Client.user_id == (user.id if user else None))
            )
        ).scalar_one_or_none()

        client_request = (
            await session.execute(
                select(ClientRequest).where(
                    ClientRequest.id == (client.selected_request_id if client else None)
                )
            )
        ).scalar_one_or_none()

        if not client_request:
            await state.clear()
            text = "❌ So‘rov topilmadi." if (user and user.lang == "uz") else "❌ Заявление не найдено."
            await message.answer(text)
            return

        # Prevent cancelling past requests
        if client_request.date.date() < datetime.now().date():
            await state.clear()
            text = "❌ Eski so'rovni bekor qilib bo'lmaydi" if (
                    user and user.lang == "uz") else "❌ Нельзя отменить старое заявление"
            await message.answer(text)
            return

        # 1) Delete children via ORM (async delete)
        cr_services = (
            await session.execute(
                select(ClientRequestService).where(
                    ClientRequestService.client_request_id == client_request.id
                )
            )
        ).scalars().all()

        for row in cr_services:
            await session.delete(row)

        # 2) Delete the request and clear selection
        await session.delete(client_request)
        if client:
            client.selected_request_id = None

        # 3) Commit once
        await session.commit()

        # cache what we need after session closes
        user_lang = user.lang if user else "uz"
        user_tgid = user.telegram_id if user else message.from_user.id

    # outside session
    await state.clear()
    text = "✅ So'rov muvaffaqiyatli bekor qilindi." if user_lang == "uz" else "✅ Заявление успешно отменено."
    keyboard = barber_menu(user_lang)
    await redis_pool.set(f"user:{user_tgid}:last_action", "barber_schedule")
    await message.answer(text, reply_markup=keyboard)
