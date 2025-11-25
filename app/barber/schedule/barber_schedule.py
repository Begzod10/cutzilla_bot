from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import selectinload
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from sqlalchemy import and_, or_, func, cast, Date, select
from app.client.models import ClientRequest
from app.barber.barber_requests.utils import recalc_schedule_stats
from datetime import timedelta, datetime
from app.barber.schedule.callback_data import (
    SchedListCB,
    DayBySidCB,
    ReqAddSvcPickCB,
    ReqOpenCB,
    ReqStatusCB,
    ReqDiscountCB,
    ReqAddSvcCB
)
from app.states import EditReqStates
from app.barber.barber_requests.utils import check_time_conflict

from app.barber.models import BarberService, BarberSchedule
from app.client.models import ClientRequestService
from app.db import AsyncSessionLocal

from app.barber.utils import (
    get_user_and_barber,
    _is_ru,
    week_bounds,
)
from app.barber.schedule.schedule_utils import (
    fetch_requests_for_day,
    fetch_requests_for_schedule,
    _sched_occupancy_stats,
    _fmt_money,
    render_request_block,
    calc_request_totals,
    _fmt_duration_minutes,
    _fmt_duration_minutes_ru,
    _final_price,
    load_request_full,
    recompute_schedule_totals,
    _day_occupancy_stats,
    _parse_discount_strict
)
from app.barber.schedule.schedule_keyboards import (
    kb_request_manage,
    kb_week_days,
    kb_add_service_list,
    kb_day_slots_by_sched,
    kb_requests_list_by_sched

)

barber_schedule = Router()


@barber_schedule.message(F.text.in_(['📅 Jadvalim', '📅 Мое расписание']))
async def get_requests(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, telegram_id)
        if not user:
            await message.answer(
                "❌ Пользователь не найден." if (lang or "").startswith("ru") else "❌ Foydalanuvchi topilmadi.")
            return
        if not barber:
            await message.answer("❌ Барбер не найден." if (lang or "").startswith("ru") else "❌ Sartarosh topilmadi.")
            return

        today = datetime.now().date()
        ru = (lang or "").startswith("ru")

        todays_requests = await fetch_requests_for_day(session, barber.id, today)
        if not todays_requests:
            header = f"📅 {'Сегодня' if ru else 'Bugungi kun'}: {today:%Y-%m-%d}"
            body = "На сегодня заявок нет." if ru else "Bugun uchun so‘rovlar yo‘q."
            initial_text = f"{header}\n\n{body}"
        else:
            blocks = [render_request_block(cr, lang) for cr in todays_requests]
            day_total_price = sum(_final_price(cr) for cr in todays_requests)
            day_total_minutes = sum(calc_request_totals(cr)[1] for cr in todays_requests)
            tm_txt = _fmt_duration_minutes_ru(day_total_minutes) if ru else _fmt_duration_minutes(day_total_minutes)

            icon, pct, _, _ = await _day_occupancy_stats(session, barber.id, today)
            pct_txt = f" {pct}%" if pct is not None else ""
            header = f"{icon}{pct_txt} {'Сегодня' if ru else 'Bugungi kun'}: {today:%Y-%m-%d}"

            unique_clients_today = len(
                {getattr(cr, "client_id", None) for cr in todays_requests if getattr(cr, "client_id", None)})
            clients_word = "клиентов" if ru else "mijoz"
            footer = (
                f"\n—\nИтого за день: {_fmt_money(day_total_price)} сум • 👥 {unique_clients_today} {clients_word} • ⏳ {tm_txt}"
                if ru else
                f"\n—\nKun bo‘yicha jami: {_fmt_money(day_total_price)} so‘m • 👥 {unique_clients_today} {clients_word} • ⏳ {tm_txt}"
            )
            initial_text = header + "\n\n" + "\n\n".join(blocks) + footer

        curr_mon, _ = week_bounds(today)
        week_kb = await kb_week_days(session, barber.id, curr_mon, lang)
        await message.answer(initial_text, reply_markup=week_kb)


@barber_schedule.callback_query(F.data.startswith("sched:week:"))
async def on_sched_week(cb: CallbackQuery, state: FSMContext):
    try:
        _, _, monday_str = cb.data.split(":", 2)
        monday = datetime.strptime(monday_str, "%Y-%m-%d").date()
    except Exception:
        await cb.answer("Bad week format", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, cb.from_user.id)
        if not barber:
            await cb.answer("Barber not found", show_alert=True)
            return

        week_kb = await kb_week_days(session, barber.id, monday, lang)

    try:
        await cb.message.edit_reply_markup(reply_markup=week_kb)
    except Exception:
        await cb.message.answer("📅", reply_markup=week_kb)
    await cb.answer()


@barber_schedule.callback_query(DayBySidCB.filter())
async def on_sched_day_by_sid(cb: CallbackQuery, callback_data: DayBySidCB, state: FSMContext):
    sched_id = int(callback_data.sid)
    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, cb.from_user.id)
        if not barber:
            await cb.answer("Barber not found", show_alert=True)
            return

        sched = await session.get(BarberSchedule, sched_id)
        if not sched or sched.barber_id != barber.id or not sched.day:
            await cb.answer("Schedule not found", show_alert=True)
            return
        barber.selected_schedule_id = sched_id
        await session.commit()
        the_day = sched.day.date()
        ru = (lang or "").startswith("ru")

        icon, pct, _, _ = await _sched_occupancy_stats(session, barber.id, sched_id, the_day)

        pct_txt = f" {pct}%" if pct is not None else ""
        header = f"{icon}{pct_txt} {'День' if ru else 'Kun'}: {the_day:%Y-%m-%d}"
        reqs = await fetch_requests_for_schedule(session, barber.id, sched_id)
        if not reqs:
            body = "На этот день заявок нет." if ru else "Bu kunda so‘rovlar yo‘q."
            text = f"{header}\n\n{body}"
        else:
            blocks = [render_request_block(cr, lang) for cr in reqs]
            total_price = sum(_final_price(cr) for cr in reqs)
            total_minutes = sum(calc_request_totals(cr)[1] for cr in reqs)
            unique_clients = len({getattr(cr, "client_id", None) for cr in reqs if getattr(cr, "client_id", None)})
            tm_txt = _fmt_duration_minutes_ru(total_minutes) if ru else _fmt_duration_minutes(total_minutes)
            clients_word = "клиентов" if ru else "mijoz"
            footer = (
                f"\n—\nИтого: {_fmt_money(total_price)} сум • 👥 {unique_clients} {clients_word} • ⏳ {tm_txt}"
                if ru else
                f"\n—\nJami: {_fmt_money(total_price)} so‘m • 👥 {unique_clients} {clients_word} • ⏳ {tm_txt}"
            )
            text = header + "\n\n" + "\n\n".join(blocks) + footer

        # slot keyboard (30-minute slots) still date-based
        slots_kb = await kb_day_slots_by_sched(session, barber.id, sched_id, slot_minutes=30)

        # add "Requests" opener using schedule id with pagination start page=1
        title_req = "Заявки" if ru else "So'rovlar"
        req_btn = InlineKeyboardButton(
            text=f"📋 {title_req} ({len(reqs)})",
            callback_data=SchedListCB(sid=sched_id, page=1).pack()
        )
        slots_kb = InlineKeyboardMarkup(inline_keyboard=[[req_btn]] + list(slots_kb.inline_keyboard or []))

    try:
        await cb.message.edit_text(text, reply_markup=slots_kb)
    except Exception:
        await cb.message.answer(text, reply_markup=slots_kb)
    await cb.answer()


@barber_schedule.callback_query(SchedListCB.filter())
async def on_req_list_by_sid(cb: CallbackQuery, callback_data: SchedListCB, state: FSMContext):
    sched_id = int(callback_data.sid)
    page = int(callback_data.page)

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, cb.from_user.id)
        if not barber:
            await cb.answer("Barber not found", show_alert=True)
            return
        kb = await kb_requests_list_by_sched(session, barber.id, sched_id, lang, page)

    try:
        await cb.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        await cb.message.answer("📋", reply_markup=kb)
    await cb.answer()


# ---- OPEN REQUEST (ro:)
@barber_schedule.callback_query(ReqOpenCB.filter())
async def on_req_open(cb: CallbackQuery, callback_data: ReqOpenCB, state: FSMContext):
    req_id = int(callback_data.req_id)
    sched_id = int(callback_data.sid)
    page = int(callback_data.page)

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, cb.from_user.id)
        if not barber:
            await cb.answer("Barber not found", show_alert=True)
            return

        cr = await load_request_full(session, barber.id, req_id)
        if not cr or cr.barber_id != barber.id:
            await cb.answer("Request not found", show_alert=True)
            return

        text = "🧾 " + render_request_block(cr, lang)
        kb = kb_request_manage(req_id, sched_id, lang, getattr(cr, "status", None), page)

    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


# ---- STATUS CHANGE (rs:)
# ---- Status handler that USES the parsed CallbackData ----
@barber_schedule.callback_query(ReqStatusCB.filter())
async def on_req_status(cb: CallbackQuery, callback_data: ReqStatusCB, state: FSMContext):
    req_id = int(callback_data.req_id)
    sched_id = int(callback_data.sid)
    action = (callback_data.action or "").lower()
    page = int(callback_data.page or 1)

    if action not in {"accept", "deny"}:
        await cb.answer("Bad status action", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, cb.from_user.id)
        if not barber:
            await cb.answer("Barber not found", show_alert=True)
            return

        ru = _is_ru(lang)

        # 🔒 Load request with row-level lock to prevent concurrent modifications
        stmt = (
            select(ClientRequest)
            .where(
                and_(
                    ClientRequest.id == req_id,
                    ClientRequest.barber_id == barber.id
                )
            )
            .options(
                selectinload(ClientRequest.services)
                .selectinload(ClientRequestService.barber_service)
                .selectinload(BarberService.service),
                selectinload(ClientRequest.client),
                selectinload(ClientRequest.barber),
                selectinload(ClientRequest.scores),
                selectinload(ClientRequest.schedule_details),
            )
            .with_for_update()  # ✅ Lock the row
        )

        result = await session.execute(stmt)
        cr = result.scalar_one_or_none()

        if not cr:
            await cb.answer(
                "Запрос не найден" if ru else "So'rov topilmadi",
                show_alert=True
            )
            return



        # Find the effective day to compare with "today"
        sched = await session.get(BarberSchedule, sched_id)
        if sched and sched.barber_id != barber.id:
            await cb.answer(
                "График не найден" if ru else "Jadval topilmadi",
                show_alert=True
            )
            return

        if sched and sched.day:
            eff_day = sched.day.date()
        elif cr.from_time:
            eff_day = cr.from_time.date()
        elif cr.date:
            eff_day = cr.date.date()
        else:
            eff_day = None  # if completely undated, allow as a fallback

        today = datetime.now().date()
        if eff_day and eff_day < today:
            msg = (
                "Нельзя менять статус для прошедшего дня."
                if ru
                else "O'tgan kun uchun holatni o'zgartirib bo'lmaydi."
            )
            await cb.answer(msg, show_alert=True)
            return

        # ✅ Check for time conflicts BEFORE accepting
        if action == "accept":
            if cr.from_time and cr.to_time:
                has_conflict = await check_time_conflict(
                    session,
                    barber.id,
                    cr.from_time,
                    cr.to_time,
                    exclude_request_id=req_id
                )

                if has_conflict:
                    msg = (
                        "❌ Это время уже занято! Другой запрос уже принят."
                        if ru
                        else "❌ Bu vaqt oralig'i band! Boshqa so'rov allaqachon qabul qilingan."
                    )
                    await cb.answer(msg, show_alert=True)
                    return

        # Update status
        cr.status = "accept" if action == "accept" else "deny"
        await session.flush()

        # Recompute schedule aggregates and commit
        await recalc_schedule_stats(session, sched_id)
        await session.commit()

        # Reload cr to ensure all relationships are fresh after commit
        await session.refresh(cr)

        # Render updated view
        text = "🧾 " + render_request_block(cr, lang)
        kb = kb_request_manage(cr.id, sched_id, lang, getattr(cr, "status", None), page)

    toast = (
        ("Принято" if action == "accept" else "Отклонено")
        if ru
        else ("Qabul qilindi" if action == "accept" else "Rad etildi")
    )

    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)

    await cb.answer(toast)


@barber_schedule.callback_query(ReqDiscountCB.filter())
async def on_req_discount(cb: CallbackQuery, callback_data: ReqDiscountCB, state: FSMContext):
    req_id = int(callback_data.req_id)
    sched_id = int(callback_data.sid)
    page = int(callback_data.page)

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, cb.from_user.id)
        if not barber:
            await cb.answer("Barber not found", show_alert=True)
            return

        cr = await load_request_full(session, barber.id, req_id)
        if not cr or cr.barber_id != barber.id:
            await cb.answer("Request not found", show_alert=True)
            return

    ru = _is_ru(lang)
    prompt = ("Введите скидку как число или процент (например, 15000 или 10%). Введите 0, чтобы убрать."
              if ru else
              "Chegirmani son yoki foizda kiriting (masalan, 15000 yoki 10%). O‘chirish uchun 0 yozing.")
    await state.set_state(EditReqStates.waiting_for_discount)
    await state.update_data(discount_req_id=req_id, discount_sid=sched_id, discount_page=page)
    await cb.answer()
    await cb.message.reply(prompt)


@barber_schedule.message(EditReqStates.waiting_for_discount)
async def on_discount_input(message: Message, state: FSMContext):
    data = await state.get_data()
    req_id = int(data["discount_req_id"])
    sched_id = int(data["discount_sid"])

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, message.from_user.id)
        ru = _is_ru(lang)
        if not barber:
            await message.reply("Барбер не найден." if ru else "Sartarosh topilmadi.")
            return

        # 1) Load fully (eager)
        cr = await load_request_full(session, barber.id, req_id)
        if not cr or cr.barber_id != barber.id:
            await message.reply("Заявка не найдена." if ru else "So‘rov topilmadi.")
            return

        # 2) Validate discount strictly against request subtotal
        subtotal, _ = calc_request_totals(cr)
        disc_amt, err = _parse_discount_strict(message.text, subtotal)

        if err is not None:
            if err == "gt_subtotal":
                msg = (
                    f"❌ Скидка не может превышать сумму заказа ({_fmt_money(subtotal)}). Попробуйте снова."
                    if ru else
                    f"❌ Chegirma buyurtma summasidan ({_fmt_money(subtotal)}) oshmasligi kerak. Yana urinib ko‘ring."
                )
            elif err == "neg":
                msg = "❌ Скидка не может быть отрицательной." if ru else "❌ Chegirma manfiy bo‘lishi mumkin emas."
            else:
                msg = (
                    "❌ Неверный формат. Введите число (например, 15000) или процент (например, 10%)."
                    if ru else
                    "❌ Noto‘g‘ri format. Son (masalan, 15000) yoki foiz (masalan, 10%) kiriting."
                )
            await message.reply(msg)
            # keep FSM state so they can enter again
            return

        # 3) Write discount & commit
        cr.discount = disc_amt
        await session.commit()

        # 4) Recompute schedule totals (final prices) and client count
        #    Use accepted requests attached to this schedule
        reqs_sched = await fetch_requests_for_schedule(session, barber.id, sched_id)
        total_income = sum(_final_price(r) for r in reqs_sched)
        n_clients = len({getattr(r, "client_id", None) for r in reqs_sched if getattr(r, "client_id", None)})

        sched = await session.get(BarberSchedule, sched_id)
        if sched and sched.barber_id == barber.id:
            sched.total_income = int(total_income)
            sched.n_clients = int(n_clients)
            await session.commit()

        # 5) Reload request fully for rendering (avoid lazy loads)
        cr = await load_request_full(session, barber.id, req_id)

        text = "🧾 " + render_request_block(cr, lang)
        kb = kb_request_manage(cr.id, sched_id, lang, getattr(cr, "status", None), page=1)
        await recalc_schedule_stats(session, barber.id)
        await session.commit()

    await state.clear()
    ok = "Скидка обновлена." if ru else "Chegirma yangilandi."
    await message.reply(ok)
    await message.answer(text, reply_markup=kb)


# ---- ADD SERVICE LIST (ra:)
@barber_schedule.callback_query(ReqAddSvcCB.filter())
async def on_req_addsvc(cb: CallbackQuery, callback_data: ReqAddSvcCB, state: FSMContext):
    req_id = int(callback_data.req_id)
    sched_id = int(callback_data.sid)
    page = int(callback_data.page)

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, cb.from_user.id)
        if not barber:
            await cb.answer("Barber not found", show_alert=True)
            return

        # (optional) verify request belongs to barber:
        cr = await load_request_full(session, barber.id, req_id)
        if not cr or cr.barber_id != barber.id:
            await cb.answer("Request not found", show_alert=True)
            return

        kb = await kb_add_service_list(session, barber.id, req_id, sched_id, lang, page)

    try:
        await cb.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        await cb.message.answer("➕", reply_markup=kb)
    await cb.answer()


@barber_schedule.callback_query(ReqAddSvcPickCB.filter())
async def on_req_addsvc_pick(cb: CallbackQuery, callback_data: ReqAddSvcPickCB, state: FSMContext):
    req_id = int(callback_data.req_id)
    sched_id = int(callback_data.sid)
    bs_id = int(callback_data.bs_id)
    page = int(callback_data.page)

    async with AsyncSessionLocal() as session:
        user, barber, lang = await get_user_and_barber(session, cb.from_user.id)
        ru = _is_ru(lang)
        if not barber:
            await cb.answer("Barber not found", show_alert=True)
            return

        # load request & ownership
        cr = await load_request_full(session, barber.id, req_id)
        if not cr or cr.barber_id != barber.id:
            await cb.answer("Request not found", show_alert=True)
            return

        bs = await session.get(BarberService, bs_id)
        if not bs or bs.barber_id != barber.id:
            await cb.answer("Service not found", show_alert=True)
            return

        if not (getattr(bs, "price", 0) and getattr(bs, "duration", 0)):
            await cb.answer("Услуга без цены/длительности." if ru else "Xizmatda narx/vaqt yo‘q.", show_alert=True)
            return

        # toggle add/remove
        existing = (await session.execute(
            select(ClientRequestService)
            .where(
                ClientRequestService.client_request_id == req_id,
                ClientRequestService.barber_service_id == bs_id
            )
        )).scalars().all()

        if existing:
            for row in existing:
                await session.delete(row)
            action = "removed"
        else:
            session.add(ClientRequestService(
                client_request_id=cr.id,
                barber_service_id=bs.id,
                duration=int(bs.duration),
                status=True,
            ))
            action = "added"

        # Make changes visible
        await session.flush()
        await session.refresh(cr, attribute_names=["services"])

        # ⬇️ NEW: Recompute total duration for this request and update to_time
        # Sum durations from BarberService (source of truth)
        svc_rows = (await session.execute(
            select(BarberService.duration)
            .join(ClientRequestService, ClientRequestService.barber_service_id == BarberService.id)
            .where(ClientRequestService.client_request_id == req_id)
        )).all()
        total_minutes = sum((row[0] or 0) for row in svc_rows)

        updated_end_ok = True
        trimmed = False

        if cr.from_time and total_minutes > 0:
            # Get schedule day and working hours to validate end bound
            sched = await session.get(BarberSchedule, sched_id)
            if not sched or not sched.day or not barber.start_time or not barber.end_time:
                # If no schedule/working hours, just set naive end
                cr.to_time = cr.from_time + timedelta(minutes=total_minutes)
            else:
                sched_day = sched.day.date() if hasattr(sched.day, "date") else sched.day
                new_end = cr.from_time + timedelta(minutes=total_minutes)
                work_end = datetime.combine(sched_day, barber.end_time.time())
                # Optional: also compute work_start if you want to assert start>=work_start
                # work_start = datetime.combine(sched_day, barber.start_time.time())

                if new_end <= work_end:
                    cr.to_time = new_end
                else:
                    # Don’t write an invalid end; keep previous value and notify
                    updated_end_ok = False
                    trimmed = True
        else:
            # No from_time set or no services → clear or keep to_time?
            # Choice: clear to_time when no services
            if total_minutes == 0:
                cr.to_time = None

        await recalc_schedule_stats(session, sched_id)

        await session.commit()

        # Rebuild page keyboard
        kb = await kb_add_service_list(session, barber.id, req_id, sched_id, lang, page)

    # Toasts
    base_toast = ("Добавлено" if action == "added" else "Удалено") if ru \
        else ("Qo‘shildi" if action == "added" else "O‘chirildi")

    if trimmed:
        warn = (" ⏱ превышает рабочее время" if ru else " ⏱ ish vaqtidan oshib ketdi")
        base_toast += warn

    try:
        await cb.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        await cb.message.answer("➕", reply_markup=kb)

    await cb.answer(base_toast)
