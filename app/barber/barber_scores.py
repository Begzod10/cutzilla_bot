from app.barber.models import BarberServiceScore
from app.client.models import Client
from app.barber.models import Barber, BarberService
from app.user.models import User
from app.db import AsyncSessionLocal
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

barber_scores = Router()

PAGE_SIZE = 5
TZ = ZoneInfo("Asia/Tashkent")


# -------- i18n helpers --------
def _lang_from_barber(barber):
    user = getattr(barber, "user", None)
    code = (getattr(user, "lang", None) or "").strip().lower()
    return "ru" if code.startswith("ru") else "uz"


def _t(lang, key):
    T = {
        "uz": {
            "title": "📊 Mening ballarim",
            "empty": "Hali baholar yo‘q.",
            "avg": "O‘rtacha baho",
            "count": "Umumiy soni",
            "service": "Xizmat",
            "client": "Mijoz",
            "date": "Sana",
            "time": "Vaqt",
            "comment": "Izoh",
            "prev": "⬅️ Oldingi",
            "next": "Keyingi ➡️",
            "close": "❌ Yopish",
            "page": "Sahifa",
            "not_found": "Barber topilmadi.",
        },
        "ru": {
            "title": "📊 Мои баллы",
            "empty": "Пока нет оценок.",
            "avg": "Средняя оценка",
            "count": "Всего",
            "service": "Услуга",
            "client": "Клиент",
            "date": "Дата",
            "time": "Время",
            "comment": "Комментарий",
            "prev": "⬅️ Предыдущая",
            "next": "Следующая ➡️",
            "close": "❌ Закрыть",
            "page": "Стр.",
            "not_found": "Барбер не найден.",
        },
    }
    return T["ru" if lang == "ru" else "uz"][key]


# ---------- format helpers ----------
def _stars(score_int):
    s = max(0, min(5, int(score_int or 0)))
    return "⭐️" * s + "✩" * (5 - s)


def _svc_name(service, lang):
    if service is None:
        return "—"
    if lang == "ru":
        return service.name_ru or service.name_uz or service.name_en or "—"
    return service.name_uz or service.name_ru or service.name_en or "—"


def _client_name(score):
    c = getattr(score, "client", None)
    if not c:
        return "—"
    name = getattr(c, "full_name", None)
    if name:
        return name
    u = getattr(c, "user", None)
    if u and getattr(u, "full_name", None):
        return u.full_name
    return "—"


def _cr_date_time(score):
    cr = getattr(score, "client_request", None)
    if not cr or not cr.from_time:
        return "—", "—"
    ft = cr.from_time if cr.from_time.tzinfo is None else cr.from_time.astimezone(TZ).replace(tzinfo=None)
    return ft.strftime("%d.%m.%Y"), ft.strftime("%H:%M")


# ---------- DB helpers ----------
async def _count_scores(session, barber_id):
    q = select(func.count(BarberServiceScore.id)).where(
        and_(BarberServiceScore.barber_id == barber_id, BarberServiceScore.score.isnot(None))
    )
    return int((await session.execute(q)).scalar() or 0)


async def _avg_score(session, barber_id):
    q = select(func.avg(BarberServiceScore.score)).where(
        and_(BarberServiceScore.barber_id == barber_id, BarberServiceScore.score.isnot(None))
    )
    val = (await session.execute(q)).scalar()
    return float(val or 0.0)


async def _page_scores(session, barber_id, page, page_size):
    offset = max(0, (page - 1) * page_size)
    q = (
        select(BarberServiceScore)
        .options(
            selectinload(BarberServiceScore.client).selectinload(Client.user),
            selectinload(BarberServiceScore.barber_service).selectinload(BarberService.service),
            selectinload(BarberServiceScore.client_request),
        )
        .where(and_(BarberServiceScore.barber_id == barber_id, BarberServiceScore.score.isnot(None)))
        .order_by(BarberServiceScore.id.desc())
        .limit(page_size)
        .offset(offset)
    )
    result = await session.execute(q)
    return result.scalars().all()


# ---------- UI ----------
def _kb(page, total_pages, lang):
    rows = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text=_t(lang, "prev"), callback_data=f"bscores:page:{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text=_t(lang, "next"), callback_data=f"bscores:page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton(text=f"{_t(lang, 'page')} {page}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton(text=_t(lang, "close"), callback_data="bscores:close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _render_scores_text(lang, avg_value, count_value, items):
    lines = [_t(lang, "title")]
    if count_value == 0:
        lines += ["", _t(lang, "empty")]
        return "\n".join(lines)

    avg_txt = f"{avg_value:.2f}".rstrip("0").rstrip(".")
    lines += ["", f"⭐ {_t(lang, 'avg')}: {avg_txt}  •  {_t(lang, 'count')}: {count_value}", ""]
    for idx, sc in enumerate(items, 1):
        svc = getattr(sc, "barber_service", None)
        svc_name = _svc_name(getattr(svc, "service", None), lang)
        client = _client_name(sc)
        d, t = _cr_date_time(sc)
        stars = _stars(getattr(sc, "score", 0))
        comment = getattr(sc, "comment", None) or "—"
        lines += [
            f"{idx}) {svc_name} — {stars}",
            f"   {_t(lang, 'client')}: {client}",
            f"   {_t(lang, 'date')}: {d}   {_t(lang, 'time')}: {t}",
            f"   {_t(lang, 'comment')}: {comment}",
            ""
        ]
    return "\n".join(lines).rstrip()


async def _send_scores_target(message_or_call, barber_id, page):
    async with AsyncSessionLocal() as session:
        barber = (await session.execute(
            select(Barber).options(selectinload(Barber.user)).where(Barber.id == barber_id)
        )).scalar_one_or_none()

        lang = _lang_from_barber(barber) if barber else "uz"
        if not barber:
            text = _t(lang, "not_found")
            if isinstance(message_or_call, Message):
                await message_or_call.answer(text)
            else:
                await message_or_call.answer(text, show_alert=True)
            return

        total = await _count_scores(session, barber_id)
        avg = await _avg_score(session, barber_id)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))

        items = await _page_scores(session, barber_id, page, PAGE_SIZE)
        text = _render_scores_text(lang, avg, total, items)
        kb = _kb(page, total_pages, lang)

    # send/edit outside of session scope
    if isinstance(message_or_call, Message):
        await message_or_call.answer(text, reply_markup=kb)
    else:
        try:
            await message_or_call.message.edit_text(text, reply_markup=kb)
        except Exception:
            await message_or_call.message.edit_reply_markup(reply_markup=kb)
        await message_or_call.answer()


# ---------- Handlers (no `session` arg!) ----------
@barber_scores.message(F.text.in_(["📊 Mening ballarim", "📊 Мои баллы"]))
async def scores_entry(message: Message, state: FSMContext):
    # find barber by telegram id using your helper
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user.scalar_one_or_none()
        barber = await session.execute(select(Barber).where(Barber.user_id == user.id))
        barber = barber.scalar_one_or_none()
        if not barber:
            await message.answer("Barber topilmadi / Барбер не найден.")
            return
        await state.update_data(scores_page=1)
        barber_id = barber.id
    await _send_scores_target(message, barber_id, page=1)


@barber_scores.callback_query(F.data.startswith("bscores:page:"))
async def scores_pagination(call: CallbackQuery, state: FSMContext):
    try:
        page = int(call.data.split(":")[2])
    except Exception:
        await call.answer("Invalid page", show_alert=False)
        return

    async with AsyncSessionLocal() as session:
        barber = await Barber.get_user(session, call.from_user.id)
        if not barber:
            await call.answer("Barber not found", show_alert=True)
            return
        await state.update_data(scores_page=page)
        barber_id = barber.id
    await _send_scores_target(call, barber_id, page=page)


@barber_scores.callback_query(F.data == "bscores:close")
async def scores_close(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        await call.message.edit_reply_markup(reply_markup=None)
    await call.answer()
