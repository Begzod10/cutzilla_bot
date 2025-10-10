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
from app.client.models import Client, ClientRequest, ClientRequestService, ClientBarbers
from .keyboards import create_score_keyboard, overall_skip_comment_kb, make_my_barbers_keyboard
from .utils import find_free_slots  # if you still use it elsewhere

from app.states import ScoreState
from app.db import AsyncSessionLocal

client_barber_list_router = Router()


@client_barber_list_router.message(F.text.in_(["🪮 Мои барберы", "🪮 Mening barberlarim"]))
async def client_barber_list(message: Message, state: FSMContext):
    user = message.from_user
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == user.id))).scalar_one_or_none()
        lang = getattr(user, "lang", "ru") if user else "ru"
        client = (await session.execute(select(Client).where(Client.user_id == user.id).limit(1))).scalar_one_or_none()
        client_barbers = (
            await session.execute(
                select(ClientBarbers)
                .where(ClientBarbers.client_id == client.id)
                .options(selectinload(ClientBarbers.barber).selectinload(Barber.user))
            )
        ).scalars().all()

        if not client_barbers:
            await message.answer(
                "🪮 У вас пока нет сохранённых барберов."
                if lang == "ru"
                else "🪮 Sizda hozircha saqlangan barberlar yo‘q."
            )
        else:
            kb = make_my_barbers_keyboard(client_barbers, lang)
            await message.answer(
                "🪮 Мои барберы:" if lang == "ru" else "🪮 Mening barberlarim:",
                reply_markup=kb
            )
