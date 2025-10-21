from datetime import date, datetime, time
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import and_, or_, func, cast, Date, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import distinct
from app.barber.models import Barber, BarberService, BarberSchedule
from app.client.models import Client, ClientRequest, ClientRequestService
from app.db import AsyncSessionLocal  # ← ensure correct import path
from app.user.models import User
from .keyboards import (
    request_row_kb,
    build_profile_button

)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

barber_requests = Router()

PAGE_SIZE = 5


def _status_title(status: str, lang: str) -> str:
    ru = (lang or "").lower().startswith("ru")
    mapping = {
        "pending": ("⏳ Kutilayotgan", "⏳ В ожидании"),
        "accept": ("✅ Qabul qilingan", "✅ Принятые"),
        "deny": ("❌ Rad etilgan", "❌ Отклонённые"),
    }
    uz, ru_t = mapping.get(status, ("⏳ Kutilayotgan", "⏳ В ожидании"))
    return ru_t if ru else uz


def _filter_tabs_kb(active_status: str, page: int, lang: str) -> list[list[InlineKeyboardButton]]:
    # show three tabs, active one is "dimmed"
    def tab(status, text):
        if status == active_status:
            return InlineKeyboardButton(text=f"• {text} •", callback_data="noop")
        return InlineKeyboardButton(text=text, callback_data=f"reqflt:{status}:1")

    uz = not (lang or "").lower().startswith("ru")
    texts = {
        "pending": "⏳ Kutilayotgan" if uz else "⏳ В ожидании",
        "accept": "✅ Qabul qilingan" if uz else "✅ Принятые",
        "deny": "❌ Rad etilgan" if uz else "❌ Отклонённые",
    }
    return [[
        tab("pending", texts["pending"]),
        tab("accept", texts["accept"]),
        tab("deny", texts["deny"]),
    ]]


def _nav_row_kb(status: str, page: int, has_prev: bool, has_next: bool, lang: str) -> list[InlineKeyboardButton]:
    btns = []
    if has_prev:
        btns.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"reqpage:{status}:{page - 1}"))
    btns.append(InlineKeyboardButton(text="🔄 Refresh", callback_data=f"reqpage:{status}:{page}"))
    if has_next:
        btns.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"reqpage:{status}:{page + 1}"))
    return btns


async def _build_requests_query(status: str, barber_id: int):
    now = datetime.now()
    today = date.today()
    base = select(ClientRequest).where(
        ClientRequest.barber_id == barber_id,
        ClientRequest.status == status,
    )
    if status == "pending":
        base = base.where(or_(
            and_(ClientRequest.from_time.is_not(None), ClientRequest.from_time >= now),
            and_(ClientRequest.from_time.is_(None), cast(ClientRequest.date, Date) >= today),
        ))
    else:
        base = base.where(cast(ClientRequest.date, Date) >= today)

    return base.order_by(func.coalesce(ClientRequest.from_time, ClientRequest.date).asc()).options(
        selectinload(ClientRequest.services)
        .selectinload(ClientRequestService.barber_service)
        .selectinload(BarberService.service),
        selectinload(ClientRequest.client).selectinload(Client.user),
    )


async def _count_requests(session, q):
    # Convert the selectable to a subquery and count rows
    sub = q.subquery()
    cnt_q = select(func.count()).select_from(sub)
    return (await session.execute(cnt_q)).scalar_one() or 0


def _paginate(items, page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


def _list_header(lang: str, status: str, page: int, total: int):
    today = date.today().strftime('%Y-%m-%d')
    title = _status_title(status, lang)
    ru = (lang or "").lower().startswith("ru")
    if ru:
        return f"📨 {title}\n📅 На {today}\n📄 Страница {page} (всего {total})"
    return f"📨 {title}\n📅 {today} holati\n📄 {page}-sahifa (jami {total})"


def _wrap_nav_kb(active_status: str, page: int, has_prev: bool, has_next: bool, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        *_filter_tabs_kb(active_status, page, lang),
        _nav_row_kb(active_status, page, has_prev, has_next, lang)
    ])
    return kb


async def _send_requests_page(message: Message, barber_id: int, lang: str, status: str, page: int = 1,
                              page_size: int = PAGE_SIZE):
    async with AsyncSessionLocal() as session:
        q = await _build_requests_query(status, barber_id)
        result = await session.execute(q)
        all_items = result.scalars().all()
        total = len(all_items)
        if total == 0:
            await message.answer(_t("no_requests", lang), reply_markup=_wrap_nav_kb(status, page, False, False, lang))
            return

        # current page slice
        page_items = _paginate(all_items, page, page_size)
        has_prev = page > 1
        has_next = (page * page_size) < total

        # header with tabs + nav
        await message.answer(_list_header(lang, status, page, total),
                             reply_markup=_wrap_nav_kb(status, page, has_prev, has_next, lang))

        # render each item as your existing detailed card with Accept/Deny + profile
        for cr in page_items:
            d = cr.date.strftime('%Y-%m-%d') if cr.date else "—"
            ft = cr.from_time.strftime('%H:%M') if cr.from_time else "—"
            tt = cr.to_time.strftime('%H:%M') if cr.to_time else "—"
            cmt = cr.comment or "—"

            client_user = getattr(getattr(cr, "client", None), "user", None)
            client_fullname = "—"
            if client_user:
                first = getattr(client_user, "name", "") or ""
                last = getattr(client_user, "surname", "") or ""
                client_fullname = (f"{first} {last}").strip() or "—"

            svc_lines, total_price, total_duration = [], 0, 0
            for crs in (cr.services or []):
                bs = getattr(crs, "barber_service", None)
                svc = getattr(bs, "service", None) if bs else None

                price = getattr(bs, "price", 0) if bs and (bs.price is not None) else 0
                total_price += price

                dur_mins = (
                    crs.duration if (hasattr(crs, "duration") and crs.duration is not None)
                    else (
                        bs.duration if (bs is not None and hasattr(bs, "duration") and bs.duration is not None) else 0)
                )
                total_duration += int(dur_mins or 0)

                svc_name = _service_name_by_lang(svc, lang)
                svc_lines.append(f"    • {svc_name} — {_fmt_money(price)} so'm — ⏱ {_fmt_duration(dur_mins)}")

            services_block = "\n".join(svc_lines) if svc_lines else "    —"

            text = (
                f"👤 Mijoz: {client_fullname}\n"
                f"  📅 {d}\n"
                f"  🕘 So‘ralgan vaqt: {ft}–{tt}\n"
                f"  🧾 {cmt}\n"
                f"  🧰 Xizmatlar:\n{services_block}\n"
                f"  💵 Jami: {_fmt_money(total_price)} so'm\n"
                f"  ⏳ Umumiy davomiylik: {_fmt_duration(total_duration)}"
            )

            kb = request_row_kb(cr.id, lang)
            if client_user:
                prof_btn = build_profile_button(client_user, lang)
                if prof_btn:
                    kb.inline_keyboard.append([prof_btn])

            await message.answer(text, reply_markup=kb)


async def _notify_client_about_request(bot, session, cr):
    """
    Sends localized message to the client when barber accepts/denies a request.
    Uses cr.status ('accept'|'deny').
    """
    # Load client user
    client = cr.client
    if not client:
        return
    client_user = await session.get(User, client.user_id)
    if not client_user or not getattr(client_user, "telegram_id", None):
        return

    lang = (getattr(client_user, "lang", "uz") or "uz").lower()

    # Build service lines & totals
    total_price, total_duration = 0, 0
    sv_lines = []
    for crs in (cr.services or []):
        bs = crs.barber_service
        svc = getattr(bs, "service", None)
        name_uz = getattr(svc, "name_uz", "—") if svc else "—"
        name_ru = getattr(svc, "name_ru", "—") if svc else "—"
        price = (getattr(bs, "price", 0) or 0)
        dur = (getattr(crs, "duration", None) or getattr(bs, "duration", 0) or 0)
        total_price += price
        total_duration += dur
        svc_name = name_ru if lang == "ru" else name_uz
        price_unit = "сум" if lang == "ru" else "so'm"
        min_unit = "мин" if lang == "ru" else "min"

        sv_lines.append(f"{svc_name}: {price} {price_unit}, {dur} {min_unit}")
    services_text = "\n".join(sv_lines) if sv_lines else ("—" if lang == "ru" else "—")

    # Times
    day_dt = cr.date or cr.from_time or datetime.now()
    if hasattr(day_dt, "date"):
        day_str = (day_dt.date() if isinstance(day_dt, datetime) else day_dt).strftime("%d.%m.%Y")
    else:
        day_str = datetime.now().strftime("%d.%m.%Y")

    def _fmt(t):
        if not t:
            return "—"
        if isinstance(t, datetime):
            return t.strftime("%H:%M")
        return getattr(t, "strftime", lambda *_: "—")("%H:%M")

    ft = _fmt(cr.from_time)
    tt = _fmt(cr.to_time)

    price_unit = "сум" if lang == "ru" else "so'm"
    min_unit = "мин" if lang == "ru" else "min"

    if cr.status == "accept":
        text = (
            f"✅ So'rovingiz tasdiqlandi!\n"
            f"📆 Sana: {day_str}\n"
            f"🕒 Vaqt: {ft} – {tt}\n"
            f"🛠️ Xizmatlar:\n{services_text}\n"
            f"⏱️ Umumiy davomiylik: {total_duration} {min_unit}\n"
            f"💰 Umumiy narx: {total_price} {price_unit}"
        ) if lang != "ru" else (
            f"✅ Ваша заявка подтверждена!\n"
            f"📆 Дата: {day_str}\n"
            f"🕒 Время: {ft} – {tt}\n"
            f"🛠️ Услуги:\n{services_text}\n"
            f"⏱️ Общая продолжительность: {total_duration} {min_unit}\n"
            f"💰 Общая сумма: {total_price} {price_unit}"
        )
    else:  # deny
        text = (
            f"❌ Kechirasiz, so'rovingiz rad etildi.\n"
            f"📆 Sana: {day_str}\n"
            f"🕒 Vaqt: {ft} – {tt}\n"
            f"🛠️ Xizmatlar:\n{services_text}\n\n"
            f"⏱️ Umumiy davomiylik: {total_duration} {min_unit}\n"
            f"💰 Umumiy narx: {total_price} {price_unit}\n\n"
            f"⏭️ Iltimos, boshqa vaqtni tanlab ko'ring."
        ) if lang != "ru" else (
            f"❌ К сожалению, ваша заявка отклонена.\n"
            f"📆 Дата: {day_str}\n"
            f"🕒 Время: {ft} – {tt}\n"
            f"🛠️ Услуги:\n{services_text}\n\n"
            f"⏱️ Общая продолжительность: {total_duration} {min_unit}\n"
            f"💰 Общая сумма: {total_price} {price_unit}\n\n"
            f"⏭️ Пожалуйста, выберите другое время."
        )

    try:
        await bot.send_message(client_user.telegram_id, text)
    except Exception:
        pass


def _fmt_duration(mins: Optional[int]) -> str:
    if not mins:
        return "00:00"
    h, m = divmod(int(mins), 60)
    return f"{h:02d}:{m:02d}"


def _service_name_by_lang(svc, lang: str) -> str:
    if not svc:
        return "—"
    lang = (lang or "").lower()
    if lang.startswith("ru"):
        return (getattr(svc, "name_ru", None)
                or getattr(svc, "name_uz", None)
                or getattr(svc, "name_en", None)
                or "—")
    elif lang.startswith("en"):
        return (getattr(svc, "name_en", None)
                or getattr(svc, "name_uz", None)
                or getattr(svc, "name_ru", None)
                or "—")
    else:
        return (getattr(svc, "name_uz", None)
                or getattr(svc, "name_ru", None)
                or getattr(svc, "name_en", None)
                or "—")


def _fmt_money(val: int) -> str:
    return f"{val:,}".replace(",", " ")


def _t(key: str, lang: str) -> str:
    ru = (lang or "").lower().startswith("ru")
    vocab = {
        "header": "📨 Новые запросы (по {date}):" if ru else "📨 Yangi so‘rovlar (bugungacha): {date}",
        "no_requests": "✅ Новых запросов на сегодня нет." if ru else "✅ Buguncha yangi so‘rovlar yo‘q.",
        "id": "ID",
        "date": "📅",
        "time": "⏰",
        "comment": "🧾",
        "services": "🧰 Услуги" if ru else "🧰 Xizmatlar",
        "total": "💵 Итого" if ru else "💵 Jami",
        "cur": "сум" if ru else "so'm",
        "accepted_toast": "✅ Принято" if ru else "✅ Qabul qilindi",
        "denied_toast": "❌ Отклонено" if ru else "❌ Rad etildi",
        "bad_action": "❌ Неверное действие" if ru else "❌ Noto‘g‘ri amal",
        "not_found": "❌ Запрос не найден." if ru else "❌ So‘rov topilmadi.",
        "user_not_found": "❌ Пользователь не найден." if ru else "❌ User not found.",
        "barber_not_found": "❌ Профиль барбера не найден." if ru else "❌ Barber profile not found.",
    }
    return vocab[key]


async def recalc_schedule_stats(session: AsyncSessionLocal, schedule_id: int) -> None:
    # 1) Number of accepted client requests for this schedule
    n_clients_q = (
        select(func.count(distinct(ClientRequest.id)))
        .where(
            ClientRequest.barber_schedule_id == schedule_id,
            ClientRequest.status == "accept",
        )
    )
    n_clients = (await session.execute(n_clients_q)).scalar_one() or 0

    # 2) Total income: sum of service prices for accepted requests on this schedule
    #    client_requests_services -> barber_services (price)
    total_income_q = (
        select(func.coalesce(func.sum(BarberService.price), 0))
        .select_from(ClientRequestService)
        .join(ClientRequest, ClientRequestService.client_request_id == ClientRequest.id)
        .join(BarberService, ClientRequestService.barber_service_id == BarberService.id)
        .where(
            ClientRequest.barber_schedule_id == schedule_id,
            ClientRequest.status == "accept",
        )
    )
    total_income = (await session.execute(total_income_q)).scalar_one() or 0

    # 3) Persist on the schedule row
    schedule: BarberSchedule = await session.get(BarberSchedule, schedule_id)
    if schedule:
        schedule.n_clients = int(n_clients)
        schedule.total_income = int(total_income)
        await session.commit()


@barber_requests.message(F.text.in_(['📨 So‘rovlar', '📨 Запросы']))
async def requests_list(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user: Optional[User] = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        if not user:
            await message.answer(_t("user_not_found", "uz"))
            return
        lang = getattr(user, "lang", "uz") or "uz"
        barber: Optional[Barber] = (
            await session.execute(select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login))
        ).scalar_one_or_none()
        if not barber:
            await message.answer(_t("barber_not_found", lang))
            return

    # show PENDING page 1 (it will append cards below header)
    await _send_requests_page(message, barber.id, lang, status="pending", page=1, page_size=PAGE_SIZE)


@barber_requests.callback_query(F.data.startswith("reqflt:"))
async def switch_filter_tab(cb: CallbackQuery):
    try:
        _, status, page_str = cb.data.split(":")
        page = int(page_str)
    except Exception:
        await cb.answer("Bad filter", show_alert=True)
        return

    telegram_id = cb.from_user.id
    async with AsyncSessionLocal() as session:
        user: Optional[User] = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        if not user:
            await cb.answer(_t("user_not_found", "uz"), show_alert=True)
            return
        lang = getattr(user, "lang", "uz") or "uz"
        barber: Optional[Barber] = (
            await session.execute(select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login))
        ).scalar_one_or_none()
        if not barber:
            await cb.answer(_t("barber_not_found", lang), show_alert=True)
            return

    # Append the new page below; keep existing messages (so "new data" is added, not replaced)
    await _send_requests_page(cb.message, barber.id, lang, status=status, page=page, page_size=PAGE_SIZE)
    await cb.answer()


# ----- Inline callbacks: pagination -----
@barber_requests.callback_query(F.data.startswith("reqpage:"))
async def paginate_requests(cb: CallbackQuery):
    try:
        _, status, page_str = cb.data.split(":")
        page = int(page_str)
    except Exception:
        await cb.answer("Bad page", show_alert=True)
        return

    telegram_id = cb.from_user.id
    async with AsyncSessionLocal() as session:
        user: Optional[User] = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        if not user:
            await cb.answer(_t("user_not_found", "uz"), show_alert=True)
            return
        lang = getattr(user, "lang", "uz") or "uz"
        barber: Optional[Barber] = (
            await session.execute(select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login))
        ).scalar_one_or_none()
        if not barber:
            await cb.answer(_t("barber_not_found", lang), show_alert=True)
            return

    # As with filter switch, just append the requested page
    await _send_requests_page(cb.message, barber.id, lang, status=status, page=page, page_size=PAGE_SIZE)
    await cb.answer()


@barber_requests.callback_query(F.data.startswith("req:"))
async def handle_request_action(call: CallbackQuery):
    try:
        _, req_id_str, action = call.data.split(":")
        req_id = int(req_id_str)
    except Exception:
        await call.answer("❌ Noto‘g‘ri amal ma’lumoti.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        cr = await session.get(
            ClientRequest, req_id,
            options=[
                selectinload(ClientRequest.services)
                .selectinload(ClientRequestService.barber_service)
                .selectinload(BarberService.service),
                selectinload(ClientRequest.client),
            ]
        )
        if not cr:
            await call.answer("❌ So‘rov topilmadi.", show_alert=True)
            return
        cr.status = action
        await session.commit()
        if action == "accept":
            # Recalculate schedule totals
            if cr.barber_schedule_id:
                await recalc_schedule_stats(session, cr.barber_schedule_id)
            try:
                await call.message.edit_reply_markup()
            except Exception:
                pass
            await call.answer("✅ Qabul qilindi.", show_alert=False)
            await call.message.answer(f"✅ So‘rov qabul qilindi .")
            await _notify_client_about_request(call.bot, session, cr)
        elif action == "deny":
            # Recalculate schedule totals too (denial may reduce totals)
            if cr.barber_schedule_id:
                await recalc_schedule_stats(session, cr.barber_schedule_id)

            try:
                await call.message.edit_reply_markup()
            except Exception:
                pass

            await call.answer("❌ Rad etildi.", show_alert=False)
            await call.message.answer(f"❌ So‘rov rad etildi .")
            await _notify_client_about_request(call.bot, session, cr)
        else:
            await call.answer("❌ Noto‘g‘ri amal.", show_alert=True)
