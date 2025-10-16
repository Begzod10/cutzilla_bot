from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.barber.models import BarberSchedule
from aiogram.types import CallbackQuery
from app.barber.schedule.schedule_utils import _working_time_windows, _overlaps, fetch_requests_for_schedule
from datetime import datetime, timedelta, time, date
from typing import List, Tuple
from .callback_data import SchedPickSlotCBClient, SchedPickSlotCBClientEdit
from typing import List, Optional

def location_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "ru":
        location_text = "📍 Отправить мою локацию"
        back_text = "⬅️ Назад"
    else:  # default uz
        location_text = "📍 Lokatsiyamni yuborish"
        back_text = "⬅️ Orqaga"

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=location_text, request_location=True),
                KeyboardButton(text=back_text)
            ]
        ],
        resize_keyboard=True
    )

    return keyboard


def _t(lang, ru, uz):
    return ru if lang == "ru" else uz


def make_barbers_keyboard_rows(rows, lang: str, page: int, total_pages: int, include_filter_button: bool):
    kb_rows = []

    # Group barbers two per row
    row_buffer = []
    for (barber_id, score, name, surname) in rows:
        full_name = f"{name or ''} {surname or ''}".strip() or "—"
        shown_score = score if score is not None else "—"

        btn = InlineKeyboardButton(
            text=f"{full_name} ⭐ {shown_score}",
            callback_data=f"select_barber:{barber_id}"
        )
        row_buffer.append(btn)

        # flush every 2
        if len(row_buffer) == 2:
            kb_rows.append(row_buffer)
            row_buffer = []

    # if odd number of barbers → last single button
    if row_buffer:
        kb_rows.append(row_buffer)

    # pager row
    pager = []
    if page > 1:
        pager.append(InlineKeyboardButton(text="« Prev", callback_data=f"barbers_page:{page - 1}"))
    if page < total_pages:
        pager.append(InlineKeyboardButton(text="Next »", callback_data=f"barbers_page:{page + 1}"))
    if pager:
        kb_rows.append(pager)

    # filter button row
    if include_filter_button:
        kb_rows.append([
            InlineKeyboardButton(
                text=_t(lang, "🔎 Изменить регион/город", "🔎 Region/shaharni o‘zgartirish"),
                callback_data="open_filter"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def create_regions_keyboard(regions, lang="ru"):
    rows = []
    row_buffer = []

    for r in regions:
        name = r.name_ru if lang == "ru" else r.name_uz
        if not name:
            name = getattr(r, "name", None) or "—"

        text = str(name).strip()[:64]
        region_id = getattr(r, "id", None)
        if region_id is None:
            continue

        row_buffer.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"choose_region:{region_id}"
            )
        )

        if len(row_buffer) == 2:
            rows.append(row_buffer)
            row_buffer = []

    if row_buffer:  # leftover if odd count
        rows.append(row_buffer)

    # back button
    rows.append([
        InlineKeyboardButton(
            text=_t(lang, "⬅️ Назад", "⬅️ Ortga"),
            callback_data="back:root"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def create_cities_keyboard(cities, lang="ru"):
    rows = []
    row_buffer = []

    for c in cities:
        name = (c.name_ru if lang == "ru" else c.name_uz) if hasattr(c, "name_ru") else (
            c.get("name_ru") if lang == "ru" else c.get("name_uz")
        )
        if name:
            text = str(name).strip()[:64]
            city_id = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")
            if city_id is None:
                continue

            # add button into buffer
            row_buffer.append(InlineKeyboardButton(text=text, callback_data=f"choose_city:{city_id}"))

            # flush every 2
            if len(row_buffer) == 2:
                rows.append(row_buffer)
                row_buffer = []

    # leftover if odd count
    if row_buffer:
        rows.append(row_buffer)

    # back row
    rows.append([InlineKeyboardButton(
        text=_t(lang, "⬅️ Назад к регионам", "⬅️ Regionlarga qaytish"),
        callback_data="back:regions"
    )])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def create_back_to_cities_keyboard(lang="ru"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=_t(lang, "⬅️ Назад к городам", "⬅️ Shaharlar ro‘yxatiga qaytish"),
            callback_data="back:cities"
        ),
        InlineKeyboardButton(
            text=_t(lang, "🌍 Выбрать другой регион", "🌍 Boshqa region"),
            callback_data="back:regions"
        )
    ]])


def barber_menu(lang: str = "uz") -> ReplyKeyboardMarkup:
    ru = {
        "info": "✂️ Информация о барбере",
        "timetable": "🗓️ Расписание барбера",
        "results": "📊 Результаты заявок",
        "requests": "📋 Мои заявки",
        "back": "⬅️ Назад",
    }
    uz = {
        "info": "✂️ Sartarosh haqida",
        "timetable": "🗓️ Sartarosh jadvali",
        "results": "📊 So‘rovlar natijasi",
        "requests": "📋 So‘rovlarim",
        "back": "⬅️ Orqaga",
    }

    t = ru if lang.lower().startswith("ru") else uz

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["info"]), KeyboardButton(text=t["timetable"])],
            [KeyboardButton(text=t["results"]), KeyboardButton(text=t["requests"])],
            [KeyboardButton(text=t["back"])]
        ],
        resize_keyboard=True
    )

    return keyboard


async def send_schedule_page(message_or_callback, schedules, page, lang):
    per_page = 3
    start = page * per_page
    end = start + per_page
    page_schedules = schedules[start:end]

    # Build text
    text, keyboard = format_barber_schedule_days(page_schedules, lang)

    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"page:{page - 1}")
        )
    if end < len(schedules):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"page:{page + 1}")
        )

    if nav_buttons:
        keyboard.inline_keyboard.append(nav_buttons)

    # If it's a callback → edit message
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await message_or_callback.answer(text, reply_markup=keyboard)


def format_barber_schedule_days(schedules, user_lang: str):
    parts = []
    kb_builder = InlineKeyboardBuilder()

    for sched in schedules:
        day_str = sched.day.strftime("%d.%m.%Y") if sched.day else "?"
        header = (
            f"📅 {day_str}\n👥 Mijozlar: {sched.n_clients or 0}"
            if user_lang == "uz"
            else f"📅 {day_str}\n👥 Клиенты: {sched.n_clients or 0}"
        )
        parts.append(header)

        # Add button for that day
        kb_builder.button(
            text=day_str,
            callback_data=f"barber_day:{sched.id}"
        )

    kb_builder.adjust(2)  # 2 buttons per row
    text = "\n\n".join(parts)
    return text, kb_builder.as_markup()


def kb_with_client_back(base_kb: InlineKeyboardMarkup, lang: str = "uz") -> InlineKeyboardMarkup:
    """
    Takes kb_day_slots_by_sched(...) result and replaces the last row with a 'barber_back' row.
    """
    back_text = "⬅️ Orqaga" if lang != "ru" else "⬅️ Назад"

    rows = list(base_kb.inline_keyboard or [])
    if rows:
        # drop the last row (which contains the original back to week)
        rows = rows[:-1]
    rows.append([InlineKeyboardButton(text=back_text, callback_data="barber_back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def kb_day_slots_by_sched_client(
        session,
        barber_id: int,
        sched_id: int,
        slot_minutes: int = 30,
) -> InlineKeyboardMarkup:
    # Safety
    if slot_minutes <= 0:
        # fall back to 30 if misconfigured
        slot_minutes = 30

    sched = await session.get(BarberSchedule, sched_id)
    if not sched or sched.barber_id != barber_id or not sched.day:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⚪️ Off", callback_data="noop")
        ]])

    the_day: date = sched.day.date()
    windows = await _working_time_windows(session, barber_id, the_day)
    # normalize/sort and drop invalid windows
    windows = [(ws, we) for (ws, we) in sorted(windows) if we > ws]

    # Requests are tied to the SCHEDULE
    reqs = await fetch_requests_for_schedule(session, barber_id, sched_id)
    # Busy intervals (HH:MM only), then merge
    busy: List[Tuple[time, time]] = []
    for cr in reqs:
        ft, tt = getattr(cr, "from_time", None), getattr(cr, "to_time", None)
        if ft and tt:
            st, en = (ft.time(), tt.time()) if hasattr(ft, "time") else (ft, tt)
            if st < en:
                busy.append((st, en))
    busy.sort()
    # merge overlaps to speed checks
    merged: List[Tuple[time, time]] = []
    for st, en in busy:
        if not merged or st >= merged[-1][1]:
            merged.append((st, en))
        else:
            # overlap → extend last
            merged[-1] = (merged[-1][0], max(merged[-1][1], en))
    busy = merged
    now = datetime.now()
    is_today = (the_day == now.date())

    buttons: List[InlineKeyboardButton] = []

    for (w_start, w_end) in windows:
        cur = datetime.combine(the_day, w_start)
        end_dt = datetime.combine(the_day, w_end)

        # Build clickable slots that FINISH <= end_dt
        step = timedelta(minutes=slot_minutes)
        while cur + timedelta(minutes=slot_minutes) <= end_dt:
            s = cur.time()
            e = (cur + step).time()

            # If today, don’t allow past starts
            in_past = is_today and (cur <= now)

            is_free = all(not _overlaps(s, e, b1, b2) for (b1, b2) in busy)
            buttons.append(InlineKeyboardButton(
                text=("🟢 " if is_free else "🔴 ") + s.strftime("%H:%M"),
                callback_data=(
                    SchedPickSlotCBClient(
                        day=the_day.strftime("%Y-%m-%d"),
                        hm=s.strftime("%H%M"),
                    ).pack()
                    if is_free else "noop"
                ),
            ))
            cur += step

        # Finish tick — ALWAYS red & non-clickable (barber ends at w_end)
        buttons.append(InlineKeyboardButton(
            text="🔴 " + end_dt.strftime("%H:%M"),
            callback_data="noop",
        ))

    # 3 per row; client back
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="barber_back")])

    return InlineKeyboardMarkup(inline_keyboard=rows or [[
        InlineKeyboardButton(text="⚪️ Off", callback_data="barber_back")
    ]])


async def kb_day_slots_by_sched_client_to_change(
        session,
        barber_id: int,
        sched_id: int,
        slot_minutes: int = 30,
) -> InlineKeyboardMarkup:
    # Safety
    if slot_minutes <= 0:
        # fall back to 30 if misconfigured
        slot_minutes = 30

    sched = await session.get(BarberSchedule, sched_id)
    if not sched or sched.barber_id != barber_id or not sched.day:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⚪️ Off", callback_data="noop")
        ]])

    the_day: date = sched.day.date()
    windows = await _working_time_windows(session, barber_id, the_day)
    # normalize/sort and drop invalid windows
    windows = [(ws, we) for (ws, we) in sorted(windows) if we > ws]

    # Requests are tied to the SCHEDULE
    reqs = await fetch_requests_for_schedule(session, barber_id, sched_id)
    # Busy intervals (HH:MM only), then merge
    busy: List[Tuple[time, time]] = []
    for cr in reqs:
        ft, tt = getattr(cr, "from_time", None), getattr(cr, "to_time", None)
        if ft and tt:
            st, en = (ft.time(), tt.time()) if hasattr(ft, "time") else (ft, tt)
            if st < en:
                busy.append((st, en))
    busy.sort()
    # merge overlaps to speed checks
    merged: List[Tuple[time, time]] = []
    for st, en in busy:
        if not merged or st >= merged[-1][1]:
            merged.append((st, en))
        else:
            # overlap → extend last
            merged[-1] = (merged[-1][0], max(merged[-1][1], en))
    busy = merged
    now = datetime.now()
    is_today = (the_day == now.date())

    buttons: List[InlineKeyboardButton] = []

    for (w_start, w_end) in windows:
        cur = datetime.combine(the_day, w_start)
        end_dt = datetime.combine(the_day, w_end)

        # Build clickable slots that FINISH <= end_dt
        step = timedelta(minutes=slot_minutes)
        while cur + timedelta(minutes=slot_minutes) <= end_dt:
            s = cur.time()
            e = (cur + step).time()

            # If today, don’t allow past starts
            in_past = is_today and (cur <= now)

            is_free = all(not _overlaps(s, e, b1, b2) for (b1, b2) in busy)
            buttons.append(InlineKeyboardButton(
                text=("🟢 " if is_free else "🔴 ") + s.strftime("%H:%M"),
                callback_data=(
                    SchedPickSlotCBClientEdit(
                        day=the_day.strftime("%Y-%m-%d"),
                        hm=s.strftime("%H%M"),
                    ).pack()
                    if is_free else "noop"
                ),
            ))
            cur += step

        # Finish tick — ALWAYS red & non-clickable (barber ends at w_end)
        buttons.append(InlineKeyboardButton(
            text="🔴 " + end_dt.strftime("%H:%M"),
            callback_data="noop",
        ))

    # 3 per row; client back
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    # rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="barber_back")])

    return InlineKeyboardMarkup(inline_keyboard=rows or [[
        InlineKeyboardButton(text="⚪️ Off", callback_data="barber_back")
    ]])


# def client_request_menu(lang: str) -> ReplyKeyboardMarkup:
#     if lang == "uz":
#         buttons = [
#             [
#                 KeyboardButton(text="✂️ So'rov yuborish"),
#                 KeyboardButton(text="📋 So'rovlarim")
#             ],
#             [
#                 KeyboardButton(text="⬅️ Orqaga")
#             ]
#         ]
#     else:  # ru
#         buttons = [
#             [
#                 KeyboardButton(text="✂️ Отправить заявку"),
#                 KeyboardButton(text="📋 Мои заявки")
#             ],
#             [
#                 KeyboardButton(text="⬅️ Назад")
#             ]
#         ]
#
#     return ReplyKeyboardMarkup(
#         keyboard=buttons,
#         resize_keyboard=True
#     )


def build_barber_services_kb(
        barber_services,
        lang: str,
        selected_ids: Optional[List[int]] = None
) -> InlineKeyboardMarkup:
    if selected_ids is None:
        selected_ids = []

    service_buttons: List[InlineKeyboardButton] = []
    confirm_text = "✅ Confirm"

    for bs in barber_services:
        service = getattr(bs, "service", None)
        if not service:
            continue

        price = getattr(bs, "price", None)
        duration = getattr(bs, "duration", None)

        if lang == "uz":
            name = getattr(service, "name_uz", None) or "❓"
            price_text = (f"{price:,}".replace(",", " ") + " so'm") if price else "—"
            duration_text = (f"{duration} daqiqa") if duration else "—"
            confirm_text = "✅ Tasdiqlash"
        else:
            name = getattr(service, "name_ru", None) or "❓"
            price_text = (f"{price:,}".replace(",", " ") + " сум") if price else "—"
            duration_text = (f"{duration} минут") if duration else "—"
            confirm_text = "✅ Подтвердить"

        prefix = "✅ " if getattr(bs, "id", None) in selected_ids else ""
        button_text = f"{prefix}{name} • {price_text} • {duration_text}"

        service_buttons.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"choose_service_client:{bs.id}"
            )
        )

    # two-column rows
    rows: List[List[InlineKeyboardButton]] = [
        service_buttons[i:i + 2] for i in range(0, len(service_buttons), 2)
    ]

    # final row with Confirm
    rows.append([InlineKeyboardButton(text=confirm_text, callback_data="confirm_services")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_barber_edit_services_kb(
    barber_services,
    lang: str,
    selected_ids: Optional[List[int]] = None
) -> InlineKeyboardMarkup:
    if selected_ids is None:
        selected_ids = []

    service_buttons: List[InlineKeyboardButton] = []
    confirm_text = "✅ Confirm"

    for bs in barber_services:
        service = getattr(bs, "service", None)
        if not service:
            continue

        price = getattr(bs, "price", None)
        duration = getattr(bs, "duration", None)

        if lang == "uz":
            name = getattr(service, "name_uz", None) or "❓"
            price_text = (f"{price:,}".replace(",", " ") + " so'm") if price else "—"
            duration_text = (f"{duration} daqiqa") if duration else "—"
            confirm_text = "✅ Tasdiqlash"
        else:
            name = getattr(service, "name_ru", None) or "❓"
            price_text = (f"{price:,}".replace(",", " ") + " сум") if price else "—"
            duration_text = (f"{duration} минут") if duration else "—"
            confirm_text = "✅ Подтвердить"

        prefix = "✅ " if getattr(bs, "id", None) in selected_ids else ""
        button_text = f"{prefix}{name} • {price_text} • {duration_text}"

        service_buttons.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"edit_choose_service_client:{bs.id}"
            )
        )

    # Two-column grid for services
    rows: List[List[InlineKeyboardButton]] = [
        service_buttons[i:i+2] for i in range(0, len(service_buttons), 2)
    ]

    rows.append([
        InlineKeyboardButton(text=confirm_text, callback_data="edit_confirm_services")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _can_edit_request(cr, now: datetime = None, tzinfo=None) -> bool:
    """
    Returns True if the user can still edit the request:
    - status must be 'pending'
    - now must be at least 15 minutes before the start time
    """
    if cr.status != "pending":
        return False

    # Build the start datetime safely
    # cr.date: date or datetime, cr.from_time: time or datetime.time
    if isinstance(getattr(cr, "date", None), datetime):
        start_dt = cr.date
    else:
        # cr.date is a date; combine with from_time
        ft: time = cr.from_time if isinstance(cr.from_time, time) else cr.from_time.time()
        start_dt = datetime.combine(cr.date, ft)

    # Attach tz if naive and you use a local timezone (e.g., Asia/Tashkent)
    if start_dt.tzinfo is None and tzinfo is not None:
        start_dt = start_dt.replace(tzinfo=tzinfo)

    now = now or datetime.now(tzinfo) if tzinfo else datetime.now()

    return now <= (start_dt - timedelta(minutes=15))


def client_request_keyboard(client_request, lang: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for a specific client request in uz/ru.
    Shows 'Edit' only while pending AND >=15 minutes before start time.
    """
    if lang == "uz":
        edit_text = "✏️ So'rovni tahrirlash"
        feedback_text = "⭐ Fikr bildirish"
    else:  # ru
        edit_text = "✏️ Редактировать заявку"
        feedback_text = "⭐ Оставить отзыв"

    # If you keep everything in local time (Asia/Tashkent), set tzinfo here.
    # If your datetimes are already timezone-aware, leave tzinfo=None.
    # Example (optional):
    # import pytz
    # tzinfo = pytz.timezone("Asia/Tashkent")
    tzinfo = None

    buttons = [[InlineKeyboardButton(text=feedback_text, callback_data=f"req_feedback:{client_request.id}")]]

    if _can_edit_request(client_request, tzinfo=tzinfo):
        buttons.append([InlineKeyboardButton(text=edit_text, callback_data=f"req_details:{client_request.id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_request_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "uz":
        services_text = "💇 Xizmatlarni o‘zgartirish"
        time_text = "⏰ Vaqtni o‘zgartirish"
        cancel_text = "❌ Bekor qilish"
        back_text = "⬅️ Orqaga"
    else:  # ru
        services_text = "💇 Изменить услуги"
        time_text = "⏰ Изменить время"
        cancel_text = "❌ Отменить"
        back_text = "⬅️ Назад"

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=services_text), KeyboardButton(text=time_text)],
            [KeyboardButton(text=cancel_text), KeyboardButton(text=back_text)]
        ],
        resize_keyboard=True
    )
    return kb


def create_score_keyboard(client_request_services):
    """
    Creates an InlineKeyboardMarkup for scoring each service in a client request.
    Each row = 1 service, buttons 1–5.
    Only services with status == False will appear.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for s in client_request_services:
        service = s.barber_service
        if not service or s.status:  # skip if already scored
            continue

        buttons = [
            InlineKeyboardButton(
                text=str(i),
                callback_data=f"score:{s.client_request_id}:{service.id}:{i}"
            )
            for i in range(1, 6)
        ]
        keyboard.inline_keyboard.append(buttons)

    return keyboard


def overall_skip_comment_kb(lang: str) -> InlineKeyboardMarkup:
    text = "⏭️ Izohsiz" if (lang or "uz") == "uz" else "⏭️ Пропустить"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data="overall_skip_comment")]]
    )


def barber_list_keyboard(lang: str, barber_id: int, is_in_list: bool) -> InlineKeyboardMarkup:
    """
    Build an inline keyboard to add/remove the given barber from client's list.
    :param lang: "uz" or "ru"
    :param barber_id: current barber id
    :param is_in_list: True if the barber is already in client's list
    """
    is_uz = (lang or "uz").lower().startswith("uz")

    add_text = "➕ Barberlar ro‘yxatiga qo‘shish" if is_uz else "➕ Добавить к моим барберам"
    remove_text = "➖ Ro‘yxatimdan o‘chirish" if is_uz else "➖ Удалить из списка"

    btn_text = remove_text if is_in_list else add_text
    cb_data = f"{'removebarber' if is_in_list else 'addbarber'}:{barber_id}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data=cb_data)]
        ]
    )


def make_my_barbers_keyboard(client_barbers, lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Build an inline keyboard from a list of ClientBarbers objects.
    Shows 'Name Surname • ⭐ score'.
    """
    kb = InlineKeyboardBuilder()

    for cb in client_barbers:
        b = cb.barber
        if not b or not b.user:
            continue

        name = (b.user.name or "").strip()
        surname = (b.user.surname or "").strip()
        full_name = f"{name} {surname}".strip() or ("Без имени" if lang == "ru" else "Ismsiz")

        score = b.score if b.score is not None else "-"
        label = f"{full_name} • ⭐ {score}"

        kb.button(text=label, callback_data=f"select_barber:{b.id}")

    kb.adjust(1)
    return kb.as_markup()
