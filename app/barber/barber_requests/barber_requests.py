from datetime import date, datetime, time
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import and_, or_, func, cast, Date, select
from sqlalchemy.orm import selectinload
from .utils import check_time_conflict
from app.barber.models import Barber, BarberService, BarberSchedule
from app.client.models import Client, ClientRequest, ClientRequestService
from app.db import AsyncSessionLocal  # ← ensure correct import path
from app.user.models import User
from .utils import _t, _send_requests_page, recalc_schedule_stats, _notify_client_about_request

barber_requests = Router()

PAGE_SIZE = 5


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
        await call.answer("❌ Noto'g'ri amal ma'lumoti.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        # 🔒 Use SELECT FOR UPDATE to lock the row
        cr = await session.get(
            ClientRequest, req_id,
            options=[
                selectinload(ClientRequest.services)
                .selectinload(ClientRequestService.barber_service)
                .selectinload(BarberService.service),
                selectinload(ClientRequest.client),
            ],
            with_for_update=True  # ✅ Lock the row during transaction
        )

        if not cr:
            await call.answer("❌ So'rov topilmadi.", show_alert=True)
            return

        if action == "accept":
            # ✅ Check for time conflicts BEFORE accepting
            if cr.from_time and cr.to_time:
                has_conflict = await check_time_conflict(
                    session,
                    cr.barber_id,
                    cr.from_time,
                    cr.to_time,
                    exclude_request_id=req_id
                )

                if has_conflict:
                    await call.answer(
                        "❌ Bu vaqt oralig'i band! Boshqa so'rov allaqachon qabul qilingan.",
                        show_alert=True
                    )
                    return

            # No conflict, proceed with acceptance
            cr.status = "accept"

            # Recalculate schedule totals
            if cr.barber_schedule_id:
                await recalc_schedule_stats(session, cr.barber_schedule_id)

            await session.commit()

            try:
                await call.message.edit_reply_markup()
            except Exception:
                pass

            await call.answer("✅ Qabul qilindi.", show_alert=False)
            await call.message.answer("✅ So'rov qabul qilindi.")
            await _notify_client_about_request(call.bot, session, cr)

        elif action == "deny":
            cr.status = "deny"

            # Recalculate schedule totals
            if cr.barber_schedule_id:
                await recalc_schedule_stats(session, cr.barber_schedule_id)

            await session.commit()

            try:
                await call.message.edit_reply_markup()
            except Exception:
                pass

            await call.answer("❌ Rad etildi.", show_alert=False)
            await call.message.answer("❌ So'rov rad etildi.")
            await _notify_client_about_request(call.bot, session, cr)

        else:
            await call.answer("❌ Noto'g'ri amal.", show_alert=True)
