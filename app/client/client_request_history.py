from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.states import BookingState
from app.user.models import User
from app.barber.models import Barber, BarberService, BarberSchedule, BarberScheduleDetail, BarberServiceScore
from app.service.models import Service
from app.client.models import Client, ClientRequest, ClientRequestService
from .keyboards import create_score_keyboard, overall_skip_comment_kb
from .utils import find_free_slots  # if you still use it elsewhere

from app.states import ScoreState
from app.db import AsyncSessionLocal

client_request_history_router = Router()


@client_request_history_router.message(F.text.in_(["📊 Результаты заявок", "📊 So‘rovlar natijasi"]))
async def client_request_history(message: Message, state: FSMContext):
    # lang heuristic from the button text; you might also prefer to read from User.lang

    async with AsyncSessionLocal() as session:
        # load user
        user_obj = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        lang = user_obj.lang
        if not user_obj:
            await message.answer("❌ Client topilmadi." if lang == "uz" else "❌ Клиент не найден.")
            return

        # load client
        client = (
            await session.execute(
                select(Client).where(Client.user_id == user_obj.id)
            )
        ).scalar_one_or_none()
        if not client:
            await message.answer("❌ Client topilmadi." if lang == "uz" else "❌ Клиент не найден.")
            return

        # load completed requests, with required relations in one go
        requests_stmt = (
            select(ClientRequest)
            .options(
                selectinload(ClientRequest.barber).selectinload(Barber.user),
                selectinload(ClientRequest.services)
                .selectinload(ClientRequestService.barber_service)
                .selectinload(BarberService.service),
            )
            .where(
                ClientRequest.client_id == client.id,
                ClientRequest.barber_id == client.selected_barber,
                ClientRequest.status == "accept",
                # ClientRequest.status.is_(True),
            )
            .order_by(ClientRequest.date.desc())
        )
        client_requests = (await session.execute(requests_stmt)).scalars().all()

        if not client_requests:
            await message.answer("❌ So‘rovlar topilmadi." if lang == "uz" else "❌ Заявки не найдены.")
            return
        services_text, total_price, total_duration = "", 0, 0
        price_unit = "so'm" if lang == "uz" else "сум"
        min_unit = "min" if lang == "uz" else "мин"
        for req in client_requests:
            barber_name = (
                f"{req.barber.user.name} {req.barber.user.surname}"
                if req.barber and req.barber.user else "-"
            )
            date_str = req.date.strftime("%d-%m-%Y") if req.date else "-"

            # build services list & totals
            services_text, total_price, total_duration = "", 0, 0
            for s in req.services:
                service = s.barber_service
                if not service or not service.service:
                    continue
                service_name = service.service.name_uz if lang == "uz" else service.service.name_ru
                price = getattr(service, "price", 0) or 0
                duration = s.duration or getattr(service, "duration", 0) or 0
                total_price += price
                total_duration += duration
                services_text += f"{service_name}: {price} so'm, {duration}min\n"

            # per-service scores
            existing_scores = (
                await session.execute(
                    select(BarberServiceScore)
                    .options(selectinload(BarberServiceScore.barber_service))
                    .where(
                        BarberServiceScore.client_request_id == req.id,
                        BarberServiceScore.client_id == client.id,
                    )
                )
            ).scalars().all()

            score_text, total_score = "", 0
            if existing_scores:
                for sc in existing_scores:
                    total_score += (sc.score or 0)
                    svc_name = sc.barber_service.service.name_uz if lang == "uz" else sc.barber_service.service.name_ru
                    score_text += f"{svc_name}: {sc.score or '-'}\n"

            overall_score = (total_score / len(req.services)) if req.services else 0

            if lang == "ru":
                text = (
                    f"✂️ Мастер: {barber_name}\n"
                    f"📅 Дата: {date_str} {req.from_time.strftime('%H:%M')} - {req.to_time.strftime('%H:%M')}\n"
                    f"🛠️ Услуги:\n{services_text}"
                    f"⏱️ Общее время: {total_duration} {min_unit}\n"
                    f"💰 Общая цена: {total_price} {price_unit}\n"
                    f"⭐ Общая оценка: {overall_score}\n"
                    f"⭐ Оценки по услугам:\n{score_text}"
                    f"💬 Комментарий: {req.comment or '-'}"
                )
            else:
                text = (
                    f"✂️ Barber: {barber_name}\n"
                    f"📅 Sana: {date_str} {req.from_time.strftime('%H:%M')} - {req.to_time.strftime('%H:%M')}\n"
                    f"🛠️ Xizmatlar:\n{services_text}"
                    f"⏱️ Umumiy vaqt: {total_duration} {min_unit}\n"
                    f"💰 Umumiy narx: {total_price} {price_unit}\n"
                    f"⭐ Umumiy ball: {overall_score}\n"
                    f"⭐ Xizmatlar bo‘yicha ball:\n{score_text}"
                    f"💬 Izoh: {req.comment or '-'}"
                )

            # build keyboard for *unscored* services only
            unscored_services = [s for s in req.services if not s.status]
            keyboard = create_score_keyboard(unscored_services)

            await message.answer(text, reply_markup=(
                keyboard if keyboard and getattr(keyboard, "inline_keyboard", None) else None))


@client_request_history_router.callback_query(F.data.startswith("score:"))
async def handle_score(callback: CallbackQuery, state: FSMContext):
    # data format: "score:{request_id}:{service_id}:{score}"
    _, request_id_s, service_id_s, score_s = callback.data.split(":")
    request_id, service_id, score = int(request_id_s), int(service_id_s), int(score_s)

    async with AsyncSessionLocal() as session:
        # load user & client
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await callback.answer("❌ Foydalanuvchi topilmadi.", show_alert=True)
            return
        lang = user.lang or "uz"

        client = (
            await session.execute(
                select(Client).where(Client.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not client:
            await callback.answer("❌ Klient topilmadi.", show_alert=True)
            return
        client_request = await session.execute(
            select(ClientRequest).where(ClientRequest.id == request_id))
        client_request = client_request.scalar_one_or_none()
        # ensure this service can be scored (status == False)
        crs = (
            await session.execute(
                select(ClientRequestService).where(
                    ClientRequestService.client_request_id == request_id,
                    ClientRequestService.barber_service_id == service_id,
                    ClientRequestService.status.is_(False),
                )
            )
        ).scalar_one_or_none()
        if not crs:
            await callback.answer("❌ Siz bu xizmatga ball bera olmaysiz.", show_alert=True)
            return
        new_score = BarberServiceScore(
            client_request_id=request_id,
            client_id=client.id,
            barber_service_id=service_id,
            score=score,
            barber_id=client_request.barber_id
        )
        session.add(new_score)
        all_scores = (
            await session.execute(
                select(BarberServiceScore)
                .where(
                    BarberServiceScore.barber_id == client_request.barber_id,
                )
            )
        )

        overall_score = 0
        all_scores = all_scores.scalars().all()
        if all_scores:
            all_scores = [s.score for s in all_scores]
            overall_score = sum(all_scores) / len(all_scores)
        barber = (
            await session.execute(
                select(Barber).where(Barber.id == client_request.barber_id)
            ))
        barber = barber.scalar_one_or_none()
        if not barber:
            await callback.answer("❌ Barber topilmadi.", show_alert=True)
            return
        barber.score = overall_score
        await session.commit()
        # mark service as scored
        crs.status = True
        await session.commit()

        await callback.answer("✅ Ballingiz saqlandi!")

        # reload request with relations to rebuild message & keyboard
        req = (
            await session.execute(
                select(ClientRequest)
                .options(
                    selectinload(ClientRequest.barber).selectinload(Barber.user),
                    selectinload(ClientRequest.services)
                    .selectinload(ClientRequestService.barber_service)
                    .selectinload(BarberService.service),
                    selectinload(ClientRequest.scores),  # so we can render fresh scores if needed
                )
                .where(ClientRequest.id == request_id)
            )
        ).scalar_one_or_none()

        if not req:
            return
        barber_name = (
            f"{req.barber.user.name} {req.barber.user.surname}"
            if req.barber and req.barber.user else "-"
        )
        date_str = req.date.strftime("%d-%m-%Y") if req.date else "-"

        # services & totals
        services_text, total_price, total_duration = "", 0, 0
        for s in req.services:
            service = s.barber_service
            if not service or not service.service:
                continue
            service_name = service.service.name_uz if lang == "uz" else service.service.name_ru
            price = getattr(service, "price", 0) or 0
            duration = s.duration or getattr(service, "duration", 0) or 0
            total_price += price
            total_duration += duration
            services_text += f"{service_name}: {price} so'm, {duration}min\n"

        # per-service scores (fresh after commit)
        existing_scores = (
            await session.execute(
                select(BarberServiceScore)
                .options(selectinload(BarberServiceScore.barber_service).selectinload(BarberService.service))
                .where(
                    BarberServiceScore.client_request_id == req.id,
                    BarberServiceScore.client_id == client.id,
                )
            )
        ).scalars().all()
        score_lines, total_score = [], 0
        for sc in existing_scores:
            total_score += (sc.score or 0)
            svc_name = sc.barber_service.service.name_uz if lang == "uz" else sc.barber_service.service.name_ru
            score_lines.append(f"{svc_name}: {sc.score or '-'}")
        score_text = "\n".join(score_lines)
        overall_score = (total_score / len(req.services)) if req.services else 0
        client_request.overall_score = overall_score
        await session.commit()
        text = (
            f"✂️ Barber: {barber_name}\n"
            f"📅 Sana: {date_str} {client_request.from_time.strftime('%H:%M')} - {client_request.to_time.strftime('%H:%M')}\n"
            f"🛠️ Xizmatlar:\n{services_text}"
            f"⏱️ Umumiy vaqt: {total_duration} min\n"
            f"💰 Umumiy narx: {total_price} so'm\n"
            f"⭐ Umumiy ball: {overall_score}\n"
            f"⭐ Xizmatlar bo‘yicha ball:\n{score_text or '-'}\n"
            f"💬 Izoh: {req.comment or '-'}"
        )

        remaining = [s for s in req.services if not s.status]
    if not remaining:
        await state.update_data(overall_req_id=request_id, user_lang=lang)
        await state.set_state(ScoreState.waiting_for_overall_comment)

        prompt = (
            "📝 Barcha xizmatlarga baho berdingiz. Umumiy fikringizni yozing yoki «Izohsiz» tugmasini bosing."
            if lang == "uz"
            else "📝 Вы оценили все услуги. Напишите общий комментарий или нажмите «Пропустить»."
        )

        # show final scored state (no per-service buttons) + ask for overall comment
        await callback.message.edit_text(text)
        await callback.message.answer(prompt, reply_markup=overall_skip_comment_kb(lang))
        return
    keyboard = create_score_keyboard(remaining)
    await callback.message.edit_text(
        text,
        reply_markup=(keyboard if keyboard and getattr(keyboard, "inline_keyboard", None) else None)
    )


@client_request_history_router.message(ScoreState.waiting_for_overall_comment)
async def save_overall_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    req_id = data.get("overall_req_id")
    lang = data.get("user_lang", "uz")
    comment = (message.text or "").strip()
    if len(comment) > 255:
        comment = comment[:255]

    async with AsyncSessionLocal() as session:
        req = (
            await session.execute(
                select(ClientRequest).where(ClientRequest.id == req_id)
            )
        ).scalar_one_or_none()
        if not req:
            await state.clear()
            await message.answer("❌ So‘rov topilmadi." if lang == "uz" else "❌ Заявка не найдена.")
            return

        req.comment = comment or None
        await session.commit()

    await state.clear()
    # Edit the last bot message to remove the inline keyboard
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,  # assumes last bot message is just before user's reply
            text="✅ Izoh saqlandi." if lang == "uz" else "✅ Комментарий сохранён."
        )
    except Exception:
        # fallback if previous message can't be edited
        await message.answer("✅ Izoh saqlandi." if lang == "uz" else "✅ Комментарий сохранён.")


@client_request_history_router.callback_query(F.data == "overall_skip_comment")
async def skip_overall_comment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("user_lang", "uz")
    await state.clear()
    try:
        await callback.message.answer(
            chat_id=callback.from_user.id,
            message_id=callback.message.message_id - 1,
            text="ℹ️ Umumiy izoh kiritilmadi." if lang == "uz" else "ℹ️ Общий комментарий пропущен."
        )
        await callback.answer()
    except Exception:
        # fallback if previous message can't be edited
        await callback.message.answer(
            "ℹ️ Umumiy izoh kiritilmadi." if lang == "uz" else "ℹ️ Общий комментарий пропущен.")
