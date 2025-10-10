from datetime import date, datetime, time, timedelta
from typing import Optional, List, Tuple
from app.barber.models import (
    Barber,
    BarberWorkingDays,
    BarberService,
    BarberSchedule
)
from app.client.models import ClientRequest, ClientRequestService, Client
from sqlalchemy import select, func, cast, Date, and_, or_, distinct
from sqlalchemy.orm import selectinload
from app.barber.utils import _is_ru, _t, _fmt_d
from sqlalchemy import and_, cast, Time
from datetime import time as dtime

_UZ2IDX = {
    "dushanba": 0, "seshanba": 1, "chorshanba": 2, "payshanba": 3,
    "juma": 4, "shanba": 5, "yakshanba": 6,
}
_RU2IDX = {
    "понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3,
    "пятница": 4, "суббота": 5, "воскресенье": 6,
    "пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6,
}

UZ_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
RU_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


async def fetch_requests_for_day(
        session,
        barber_id: int,
        the_day: date,
        hm_start: Optional[time] = None,
        hm_end: Optional[time] = None,
        windows: Optional[list[tuple[time, time]]] = None,
) -> list["ClientRequest"]:
    """
    Fetch accepted requests for 'the_day'.
    - Day filter uses DATE(...) = the_day.
    - Time filter uses TIME(...) overlap with [hm_start, hm_end) OR any of 'windows'.
      If both hm_* and windows are None -> no time-of-day filter (only date filter).
    """

    # ---- date filter (same as before)
    day_filter = or_(
        and_(
            ClientRequest.from_time.is_not(None),
            cast(ClientRequest.from_time, Date) == the_day,
        ),
        and_(
            ClientRequest.from_time.is_(None),
            ClientRequest.date.is_not(None),
            cast(ClientRequest.date, Date) == the_day,
        ),
    )

    # ---- time-of-day expressions (ignore Y/M/D)
    ft_tm = cast(ClientRequest.from_time, Time)  # TIME(from_time)
    tt_tm = cast(ClientRequest.to_time, Time)  # TIME(to_time)
    dt_tm = cast(ClientRequest.date, Time)  # TIME(date) usually 00:00
    zero_tm = dtime(0, 0)

    # Fallback "end" when to_time is NULL → treat as from_time (instant) else 00:00
    eff_end = func.coalesce(tt_tm, ft_tm, zero_tm)

    # Build time filter(s) only if requested
    time_filter = None
    if windows and len(windows) > 0:
        # overlap with ANY window: (ft < w_end) AND (eff_end > w_start)
        per_window = [
            and_(ft_tm < w_end, eff_end > w_start) for (w_start, w_end) in windows
        ]
        time_filter = or_(*per_window)

    elif hm_start is not None and hm_end is not None:
        time_filter = and_(ft_tm < hm_end, eff_end > hm_start)

    # Final WHERE parts
    where_parts = [
        ClientRequest.barber_id == barber_id,
        ClientRequest.status == "accept",
        day_filter,
    ]
    if time_filter is not None:
        where_parts.append(time_filter)

    q = (
        select(ClientRequest)
        .where(*where_parts)
        .options(
            selectinload(ClientRequest.client).selectinload(Client.user),
            selectinload(ClientRequest.services)
            .selectinload(ClientRequestService.barber_service)
            .selectinload(BarberService.service),
        )
        .order_by(
            func.coalesce(ft_tm, dt_tm, zero_tm).asc(),  # order by HH:MM only
            ClientRequest.id.asc(),
        )
    )
    return (await session.execute(q)).scalars().all()


async def _booked_minutes_for_schedule(
        session, barber_id: int, sched_id: int, day: date
) -> int:
    # use schedule-scoped requests (already eager)
    reqs = await fetch_requests_for_schedule(session, barber_id, sched_id)
    windows = await _working_time_windows(session, barber_id, day)
    total = 0
    for cr in reqs:
        ft, tt = getattr(cr, "from_time", None), getattr(cr, "to_time", None)
        if not (ft and tt and ft < tt):
            continue
        ft_t, tt_t = ft.time(), tt.time()
        for ws, we in windows:
            total += _interval_overlap_minutes(ws, we, ft_t, tt_t)
    return total


async def _sched_occupancy_stats(
        session, barber_id: int, sched_id: int, day: date
) -> tuple[str, Optional[int], int, int]:
    # working minutes come from the barber’s daily windows
    total = await _total_work_minutes_for_day(session, barber_id, day)
    booked = await _booked_minutes_for_schedule(session, barber_id, sched_id, day)
    icon, pct = _occ_icon(booked, total)
    return icon, pct, booked, total


async def _ensure_req_linked_to_sched(session, req: ClientRequest, sched_id: int) -> None:
    """If request isn't attached to the schedule row, attach it."""
    if getattr(req, "barber_schedule_id", None) != sched_id:
        req.barber_schedule_id = sched_id
        await session.flush()  # no commit yet


async def recompute_schedule_totals(session, barber_id: int, sched_id: int) -> None:
    """
    total_income = sum(max(sum(service.price) - discount, 0))
    n_clients    = count(distinct client_id)
    for all ACCEPTED requests on this schedule.
    """
    # read accepted requests with services
    reqs = await fetch_requests_for_schedule(session, barber_id, sched_id)

    total_income = 0
    clients = set()
    for r in reqs:
        if getattr(r, "client_id", None):
            clients.add(r.client_id)
        total_income += _final_price(r)

    n_clients = len(clients)

    # update the schedule instance (no bulk UPDATE → no staleness)
    sched = await session.get(BarberSchedule, sched_id)
    if sched and sched.barber_id == barber_id:
        sched.total_income = int(total_income)
        sched.n_clients = int(n_clients)
        await session.flush()  # keep in current tx


def _weekday_idx_from_name(name: str) -> Optional[int]:
    if not name:
        return None
    s = name.strip().lower()
    return _UZ2IDX.get(s) or _RU2IDX.get(s)


def _week_by_monday(monday: date) -> List[date]:
    return [monday + timedelta(days=i) for i in range(7)]


def _fmt_t(dt: Optional[datetime]) -> str:
    return dt.strftime("%H:%M") if dt else "—"


def _fmt_duration_minutes(total_minutes: int) -> str:
    h, m = divmod(int(total_minutes or 0), 60)
    if h and m:
        return f"{h} soat {m} daqiqa"
    if h:
        return f"{h} soat"
    return f"{m} daqiqa"


def _fmt_duration_minutes_ru(total_minutes: int) -> str:
    h, m = divmod(int(total_minutes or 0), 60)
    if h and m:
        return f"{h} ч {m} мин"
    if h:
        return f"{h} ч"
    return f"{m} мин"


def _fmt_money(x: Optional[int]) -> str:
    return f"{int(x or 0):,}".replace(",", " ")


def _service_name(bs, lang: str) -> str:
    s = getattr(bs, "service", None)
    if not s:
        return "—"
    return getattr(s, "name_ru" if _is_ru(lang) else "name_uz", None) or getattr(s, "name", "—")


# =========================
# Pricing helpers
# =========================
def calc_request_totals(cr) -> Tuple[int, int]:
    """
    Returns (subtotal_price, total_duration_minutes) for a request using its services.
    duration priority: ClientRequestService.duration -> BarberService.duration -> 0
    price: BarberService.price -> 0
    """
    total_price = 0
    total_minutes = 0
    for crs in (cr.services or []):
        bs = crs.barber_service
        price = getattr(bs, "price", 0) or 0
        total_price += int(price)
        dur = crs.duration if (crs is not None and crs.duration is not None) else getattr(bs, "duration", 0) or 0
        total_minutes += int(dur)
    return total_price, total_minutes


def _final_price(cr) -> int:
    """Subtotal minus discount (never below 0)."""
    subtotal, _ = calc_request_totals(cr)
    disc = int(getattr(cr, "discount", 0) or 0)
    return max(subtotal - disc, 0)


def _parse_discount_strict(text: str, subtotal: int) -> tuple[Optional[int], Optional[str]]:
    """
    Returns (amount, error_code). error_code in {None, 'bad', 'neg', 'gt_subtotal'}.
    Accepts '15000' or '10%'. No clamping: will return 'gt_subtotal' if > subtotal.
    """
    t = (text or "").strip().replace(" ", "")
    if not t:
        return 0, None
    if t.endswith("%"):
        try:
            pct = float(t[:-1])
        except Exception:
            return None, "bad"
        if pct < 0:
            return None, "neg"
        amt = int(round(subtotal * (pct / 100.0)))
    else:
        try:
            amt = int(t)
        except Exception:
            return None, "bad"
        if amt < 0:
            return None, "neg"

    if amt > subtotal:
        return None, "gt_subtotal"
    return amt, None


# =========================
# Render request block
# =========================
def render_request_block(cr, lang: str) -> str:
    d = _fmt_d((cr.from_time or cr.date or datetime.now()).date())
    ft = _fmt_t(cr.from_time)
    tt = _fmt_t(cr.to_time)

    client_user = getattr(getattr(cr, "client", None), "user", None)
    full_name = "—"
    if client_user:
        first = getattr(client_user, "name", "") or ""
        last = getattr(client_user, "surname", "") or ""
        full_name = (f"{first} {last}").strip() or "—"

    status = "✅" if cr.status else "⏳"

    lines = [f"{status} #{cr.id} • {d} • {ft}–{tt} • {full_name}"]

    # services
    for crs in (cr.services or []):
        bs = crs.barber_service
        svc = _service_name(bs, lang)
        price = getattr(bs, "price", 0) or 0
        dur = crs.duration if (crs and crs.duration is not None) else getattr(bs, "duration", 0) or 0
        lines.append(f"   • {svc} — {_t(lang, f'{_fmt_money(price)} so‘m', f'{_fmt_money(price)} сум')} — ⏱ {dur} min")

    subtotal, tm = calc_request_totals(cr)
    tm_txt = _fmt_duration_minutes_ru(tm) if _is_ru(lang) else _fmt_duration_minutes(tm)
    disc = int(getattr(cr, "discount", 0) or 0)
    final = max(subtotal - disc, 0)

    if disc > 0:
        lines.append(
            f"   🧾 Subtotal: {_fmt_money(subtotal)} • 💸 Discount: -{_fmt_money(disc)}"
            if not _is_ru(lang) else
            f"   🧾 Субтотал: {_fmt_money(subtotal)} • 💸 Скидка: -{_fmt_money(disc)}"
        )

    lines.append(
        f"   {_t(lang, 'Jami', 'Итого')}: {_t(lang, f'{_fmt_money(final)} so‘m', f'{_fmt_money(final)} сум')} • ⏳ {tm_txt}"
    )
    return "\n".join(lines)


# =========================
# Occupancy helpers
# =========================
def _overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    return (a_start < b_end) and (b_start < a_end)


def _minutes_between(t1: time, t2: time) -> int:
    return (t2.hour * 60 + t2.minute) - (t1.hour * 60 + t1.minute)


async def _barber_daily_window_from_model(session, barber_id: int) -> List[Tuple[time, time]]:
    """
    Reads Barber.start_time / end_time and returns time-window(s) for a day.
    If end < start → overnight shift → split into tonight + early next day segments.
    """
    row = await session.execute(
        select(Barber.start_time, Barber.end_time).where(Barber.id == barber_id)
    )
    start_dt, end_dt = row.first() if row else (None, None)
    if not start_dt or not end_dt:
        return []

    st, et = start_dt.time(), end_dt.time()
    if st < et:
        return [(st, et)]
    elif st > et:
        return [(st, time(23, 59)), (time(0, 0), et)]
    else:
        return []


async def _working_time_windows(session, barber_id: int, day: date) -> List[Tuple[time, time]]:
    """Respects BarberWorkingDays.is_working and Barber.start_time / end_time"""
    try:
        weekday_name_uz = UZ_NAMES[day.weekday()]
        weekday_name_ru = RU_NAMES[day.weekday()]
        wd = (await session.execute(
            select(BarberWorkingDays.is_working).where(
                BarberWorkingDays.barber_id == barber_id,
                (BarberWorkingDays.name_uz == weekday_name_uz) | (BarberWorkingDays.name_ru == weekday_name_ru),
            )
        )).first()
        if wd and wd[0] is False:
            return []
    except NameError:
        pass

    win = await _barber_daily_window_from_model(session, barber_id)
    return win or []


def _interval_overlap_minutes(a_start: time, a_end: time, b_start: time, b_end: time) -> int:
    s_hm = max(a_start, b_start)
    e_hm = min(a_end, b_end)
    return max(0, (e_hm.hour * 60 + e_hm.minute) - (s_hm.hour * 60 + s_hm.minute))


async def _booked_minutes_for_day(session, barber_id: int, day: date) -> int:
    reqs = await fetch_requests_for_day(session, barber_id, day)  # status=True already in your query
    windows = await _working_time_windows(session, barber_id, day)
    total = 0
    for cr in reqs:
        ft, tt = getattr(cr, "from_time", None), getattr(cr, "to_time", None)
        if not (ft and tt and ft < tt):
            continue
        ft_t, tt_t = ft.time(), tt.time()
        for ws, we in windows:
            total += _interval_overlap_minutes(ws, we, ft_t, tt_t)
    return total


async def _total_work_minutes_for_day(session, barber_id: int, day: date) -> int:
    windows = await _working_time_windows(session, barber_id, day)
    return sum(_minutes_between(ft, tt) for ft, tt in windows if ft < tt)


def _occ_icon(booked: int, total: int) -> Tuple[str, Optional[int]]:
    if total <= 0:
        return "⚪️", None
    r = booked / total
    if r < 0.34:
        return "🟢", int(r * 100)
    if r < 0.67:
        return "🟡", int(r * 100)
    return "🔴", int(r * 100)


async def _day_occupancy_stats(session, barber_id: int, day: date) -> Tuple[str, Optional[int], int, int]:
    total = await _total_work_minutes_for_day(session, barber_id, day)
    booked = await _booked_minutes_for_day(session, barber_id, day)
    icon, pct = _occ_icon(booked, total)
    return icon, pct, booked, total


# =========================
# Queries
# =========================
async def load_request_full(session, barber_id: int, req_id: int) -> Optional[ClientRequest]:
    q = (
        select(ClientRequest)
        .where(ClientRequest.id == req_id, ClientRequest.barber_id == barber_id, ClientRequest.status == "accept")
        .options(
            selectinload(ClientRequest.client).selectinload(Client.user),
            selectinload(ClientRequest.services)
            .selectinload(ClientRequestService.barber_service)
            .selectinload(BarberService.service),
            # (optional safety) forbid any other lazy-loads:
            # raiseload("*"),
        )
        .limit(1)
    )
    return (await session.execute(q)).scalars().first()


async def fetch_requests_for_schedule(session, barber_id: int, sched_id: int) -> List["ClientRequest"]:
    q = (
        select(ClientRequest)
        .where(
            ClientRequest.barber_id == barber_id,
            ClientRequest.barber_schedule_id == sched_id,
            ClientRequest.status == "accept",
        )
        .options(
            selectinload(ClientRequest.client).selectinload(Client.user),
            selectinload(ClientRequest.services)
            .selectinload(ClientRequestService.barber_service)
            .selectinload(BarberService.service),
        )
        .order_by(ClientRequest.from_time.asc(), ClientRequest.id.asc())
    )
    return (await session.execute(q)).scalars().all()


async def _ensure_schedules_for_week(session, barber_id: int, days: List[date]) -> dict[date, BarberSchedule]:
    monday = min(days)
    start = datetime.combine(monday, time.min)
    end = datetime.combine(monday + timedelta(days=7), time.min)

    rows = (await session.execute(
        select(BarberSchedule)
        .where(
            BarberSchedule.barber_id == barber_id,
            BarberSchedule.day >= start,
            BarberSchedule.day < end,
        )
    )).scalars().all()

    by_date: dict[date, BarberSchedule] = {s.day.date(): s for s in rows if s.day}

    # create missing schedule rows so we always have sid
    to_create = [d for d in days if d not in by_date]
    for d in to_create:
        s = BarberSchedule(
            barber_id=barber_id,
            day=datetime.combine(d, time(0, 0)),
            n_clients=0,
            total_income=0,
            name_uz=UZ_NAMES[d.weekday()],
            name_ru=RU_NAMES[d.weekday()],
        )
        session.add(s)

    if to_create:
        await session.commit()
        rows = (await session.execute(
            select(BarberSchedule)
            .where(
                BarberSchedule.barber_id == barber_id,
                BarberSchedule.day >= start,
                BarberSchedule.day < end,
            )
        )).scalars().all()
        by_date = {s.day.date(): s for s in rows if s.day}

    return by_date


def _req_title(cr, lang: str) -> str:
    ft = (cr.from_time.strftime("%H:%M") if cr.from_time else "??")
    tt = (cr.to_time.strftime("%H:%M") if cr.to_time else "??")
    user = getattr(getattr(cr, "client", None), "user", None)
    full_name = "—"
    if user:
        first = getattr(user, "name", "") or ""
        last = getattr(user, "surname", "") or ""
        full_name = (f"{first} {last}").strip() or "—"
    price = _final_price(cr)
    money = _fmt_money(price)
    return f"{ft}-{tt} • {full_name} • 💰{money}"
