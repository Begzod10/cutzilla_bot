from app.barber.models import BarberSchedule, BarberService, BarberWorkingDays
from datetime import datetime, time, timedelta
from typing import List, Optional, Tuple
from app.client.models import ClientRequestService

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.barber.schedule.schedule_utils import _weekday_idx_from_name, _working_time_windows, \
    fetch_requests_for_schedule, \
    _service_name, _overlaps, _week_by_monday, _sched_occupancy_stats, _fmt_money, _req_title, \
    _ensure_schedules_for_week, UZ_NAMES, RU_NAMES
from app.barber.utils import _is_ru

from app.barber.schedule.callback_data import SchedPickSlotCB, ReqOpenCB, SchedListCB, ReqAddSvcPickCB, ReqAddSvcCB, ReqStatusCB, \
    ReqDiscountCB, DayBySidCB
from datetime import date
from sqlalchemy import select

PAGE_SIZE = 6


async def kb_day_slots_by_sched(
        session,
        barber_id: int,
        sched_id: int,
        slot_minutes: int = 30,
) -> InlineKeyboardMarkup:
    # Load schedule → get its calendar date for working windows
    sched = await session.get(BarberSchedule, sched_id)
    if not sched or sched.barber_id != barber_id or not sched.day:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⚪️ Off", callback_data="noop")
        ]])

    the_day = sched.day.date()

    windows = await _working_time_windows(session, barber_id, the_day)

    # ⬇️ IMPORTANT: requests by SCHEDULE, not by date
    reqs = await fetch_requests_for_schedule(session, barber_id, sched_id)

    # Build busy intervals using only HH:MM
    busy: List[Tuple[time, time]] = []
    for cr in reqs:
        ft, tt = getattr(cr, "from_time", None), getattr(cr, "to_time", None)
        if ft and tt and ft < tt:
            busy.append((ft.time(), tt.time()))

    # Build slot buttons
    buttons: List[InlineKeyboardButton] = []
    for (w_start, w_end) in windows:
        cur = datetime.combine(the_day, w_start)
        end_dt = datetime.combine(the_day, w_end)

        # clickable slots (e.g., 08:00..22:30 for 30-min slots)
        while cur + timedelta(minutes=slot_minutes) <= end_dt:
            s = cur.time()
            e = (cur + timedelta(minutes=slot_minutes)).time()
            free = all(not _overlaps(s, e, b1, b2) for (b1, b2) in busy)
            buttons.append(InlineKeyboardButton(
                text=("🟢 " if free else "🔴 ") + s.strftime("%H:%M"),
                callback_data=SchedPickSlotCB(
                    day=the_day.strftime("%Y-%m-%d"),
                    hm=s.strftime("%H%M"),
                ).pack() if free else "noop",
            ))
            cur += timedelta(minutes=slot_minutes)

        # ⭐ Add an end tick (23:00) colored by the last slot's availability
        last_start = (end_dt - timedelta(minutes=slot_minutes)).time()
        last_free = all(not _overlaps(last_start, end_dt.time(), b1, b2) for (b1, b2) in busy)
        buttons.append(InlineKeyboardButton(
            text="🔴 " + end_dt.strftime("%H:%M"),
            callback_data="noop",
        ))

    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(
        text="⬅️ Back",
        callback_data=f"sched:week:{(the_day - timedelta(days=the_day.weekday())):%Y-%m-%d}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows or [[
        InlineKeyboardButton(
            text="⚪️ Off",
            callback_data=f"sched:week:{(the_day - timedelta(days=the_day.weekday())):%Y-%m-%d}",
        )
    ]])


async def kb_week_days(
        session,
        barber_id: int,
        monday: date,
        lang: str = "uz",
) -> InlineKeyboardMarkup:
    """
    Week keyboard using BarberSchedule aggregates and schedule-id callbacks.
    Only shows working days (BarberWorkingDays.is_working=True).
    """
    # working weekdays
    wd_rows = (await session.execute(
        select(BarberWorkingDays.name_uz, BarberWorkingDays.name_ru, BarberWorkingDays.is_working)
        .where(BarberWorkingDays.barber_id == barber_id,
               BarberWorkingDays.is_working.is_(True))
    )).all()
    working_idxs: set[int] = set()
    for name_uz, name_ru, _ in wd_rows:
        idx = _weekday_idx_from_name(name_uz) or _weekday_idx_from_name(name_ru)
        if idx is not None:
            working_idxs.add(idx)

    days = _week_by_monday(monday)
    ru = (lang or "").lower().startswith("ru")
    names = RU_NAMES if ru else UZ_NAMES

    # ensure schedule rows exist for the week so we can always use sid
    sched_map = await _ensure_schedules_for_week(session, barber_id, days)

    prev_mon = monday - timedelta(days=7)
    next_mon = monday + timedelta(days=7)
    kb_rows = [[
        InlineKeyboardButton(text="◀️", callback_data=f"sched:week:{prev_mon:%Y-%m-%d}"),
        InlineKeyboardButton(text="▶️", callback_data=f"sched:week:{next_mon:%Y-%m-%d}"),
    ]]

    # inside kb_week_days(..):

    for d in days:
        if d.weekday() not in working_idxs:
            continue

        sched = sched_map.get(d)
        sid = sched.id
        n_clients = int(sched.n_clients or 0)
        income = int(sched.total_income or 0)

        # ⬇️ use schedule-based occupancy
        icon, pct, _booked, _total = await _sched_occupancy_stats(session, barber_id, sid, d)
        pct_txt = f" {pct}%" if pct is not None else ""

        idx = d.weekday()
        btn_text = f"{icon}{pct_txt} {names[idx]} • {d:%Y-%m-%d} • 👥{n_clients} • 💰{_fmt_money(income)}"
        kb_rows.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=DayBySidCB(sid=sid).pack()
        )])

    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


async def kb_requests_list_by_sched(session, barber_id: int, sched_id: int, lang: str,
                                    page: int = 1) -> InlineKeyboardMarkup:
    ru = _is_ru(lang)
    reqs = await fetch_requests_for_schedule(session, barber_id, sched_id)

    # pagination
    total = len(reqs)
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    slice_reqs = reqs[start:end]

    rows: List[List[InlineKeyboardButton]] = []
    for cr in slice_reqs:
        rows.append([InlineKeyboardButton(
            text=_req_title(cr, lang),
            callback_data=ReqOpenCB(req_id=cr.id, sid=sched_id, page=page).pack()
        )])

    # pagination row
    if pages > 1:
        nav_row: List[InlineKeyboardButton] = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=SchedListCB(sid=sched_id, page=page - 1).pack()))
        nav_row.append(
            InlineKeyboardButton(f"{page}/{pages}", callback_data=SchedListCB(sid=sched_id, page=page).pack()))
        if page < pages:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=SchedListCB(sid=sched_id, page=page + 1).pack()))
        rows.append(nav_row)

    back_txt = "⬅️ Назад к дню" if ru else "⬅️ Kunga qaytish"
    rows.append([InlineKeyboardButton(text=back_txt, callback_data=DayBySidCB(sid=sched_id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_request_manage(req_id: int, sched_id: int, lang: str, status: Optional[bool], page: int) -> InlineKeyboardMarkup:
    ru = _is_ru(lang)
    if status == "accept":
        status_btn = InlineKeyboardButton(
            text=("❌ Отклонить" if ru else "❌ Rad etish"),
            callback_data=ReqStatusCB(req_id=req_id, sid=sched_id, action="deny", page=page).pack()
        )
    else:
        status_btn = InlineKeyboardButton(
            text=("✅ Принять" if ru else "✅ Qabul qilish"),
            callback_data=ReqStatusCB(req_id=req_id, sid=sched_id, action="accept", page=page).pack()
        )

    discount_btn = InlineKeyboardButton(
        text=("💸 Скидка" if ru else "💸 Chegirma"),
        callback_data=ReqDiscountCB(req_id=req_id, sid=sched_id, page=page).pack()
    )

    addsvc_btn = InlineKeyboardButton(
        text=("➕ Услуга" if ru else "➕ Xizmat"),
        callback_data=ReqAddSvcCB(req_id=req_id, sid=sched_id, page=page).pack()
    )

    back_btn = InlineKeyboardButton(
        text=("⬅️ К списку" if ru else "⬅️ Ro'yxatga"),
        callback_data=SchedListCB(sid=sched_id, page=page).pack()
    )

    return InlineKeyboardMarkup(inline_keyboard=[[status_btn, discount_btn, addsvc_btn], [back_btn]])


async def kb_add_service_list(
        session,
        barber_id: int,
        req_id: int,
        sched_id: int,
        lang: str,
        page: int = 1,
) -> InlineKeyboardMarkup:
    ru = _is_ru(lang)

    # current services on this request → set of barber_service_id
    existing_ids = set(
        (await session.execute(
            select(ClientRequestService.barber_service_id)
            .where(ClientRequestService.client_request_id == req_id)
        )).scalars().all()
    )

    # only show services with price>0 and duration>0
    services = (await session.execute(
        select(BarberService)
        .where(
            BarberService.barber_id == barber_id,
            (BarberService.price != None),  # noqa
            (BarberService.price > 0),
            (BarberService.duration != None),  # noqa
            (BarberService.duration > 0),
        )
        .order_by(BarberService.id.asc())
    )).scalars().all()

    total = len(services)
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    slice_svcs = services[start:end]

    rows: List[List[InlineKeyboardButton]] = []
    for bs in slice_svcs:
        is_on = bs.id in existing_ids
        mark = "✅" if is_on else "❌"
        name = _service_name(bs, lang)
        price = _fmt_money(bs.price or 0)
        rows.append([InlineKeyboardButton(
            text=f"{mark} {name} • 💰 {price}",
            callback_data=ReqAddSvcPickCB(req_id=req_id, sid=sched_id, bs_id=bs.id, page=page).pack()
        )])

    if pages > 1:
        nav_row: List[InlineKeyboardButton] = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(
                text="◀️",
                callback_data=ReqAddSvcCB(req_id=req_id, sid=sched_id, page=page - 1).pack()
            ))
        nav_row.append(InlineKeyboardButton(
            text=f"{page}/{pages}",
            callback_data=ReqAddSvcCB(req_id=req_id, sid=sched_id, page=page).pack()
        ))
        if page < pages:
            nav_row.append(InlineKeyboardButton(
                text="▶️",
                callback_data=ReqAddSvcCB(req_id=req_id, sid=sched_id, page=page + 1).pack()
            ))
        rows.append(nav_row)

    back_txt = "⬅️ К заявке" if ru else "⬅️ So‘rovga"
    rows.append([InlineKeyboardButton(
        text=back_txt,
        callback_data=ReqOpenCB(req_id=req_id, sid=sched_id, page=page).pack()
    )])

    return InlineKeyboardMarkup(inline_keyboard=rows)
