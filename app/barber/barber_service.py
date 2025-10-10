from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, and_
from app.db import AsyncSessionLocal  # ← ensure correct import path
from app.user.models import User
from app.barber.models import Barber, BarberService
from app.service.models import Service
from .keyboards import (
    barber_services_keyboard,
    barber_service_menu_keyboard,
    service_selection_inline_keyboard,
    price_action_keyboard,
    barber_info_keyboard,  # (not used in this file but kept as before)
)
from app.basic.keyboards import back_keyboard
from app.states import BarberServiceStates, DurationStates

barber_service = Router()


@barber_service.message(F.text.in_(["➕ Xizmat qo‘shish", "➕ Добавить услугу"]))
async def add_service(message: Message, state: FSMContext):
    await state.clear()
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        # user
        user_obj = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user_obj:
            await message.answer(
                "❌ Foydalanuvchi topilmadi." if message.from_user.language_code == "uz" else "❌ Пользователь не найден.")
            return

        await redis_pool.set(f"user:{user_obj.telegram_id}:last_action", "add_service")
        lang = user_obj.lang or "uz"

        # barber
        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user_obj.id, Barber.login == user_obj.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            await message.answer("Sartarosh topilmadi." if lang == "uz" else "Парикмахер не найден.")
            return
        services_result = (await session.execute(
            select(Service).where(Service.disabled.is_(False))
        )).scalars().all()

        # barber services
        barber_services_result = (
            await session.execute(
                select(BarberService).where(BarberService.barber_id == barber.id, BarberService.is_active == True)
            )
        ).scalars().all()

        keyboard = service_selection_inline_keyboard(
            all_services=services_result,
            barber_services=barber_services_result,
            lang=lang,
        )

        await message.answer(
            "Xizmatni tanlang:" if lang == "uz" else "Выберите услугу:",
            reply_markup=keyboard,
        )
        await message.answer(".", reply_markup=back_keyboard(lang))


@barber_service.callback_query(lambda c: c.data.startswith("toggle_service:"))
async def handle_toggle_service(callback_query: CallbackQuery):
    service_id = int(callback_query.data.split(":")[1])
    redis_pool = callback_query.bot.redis

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback_query.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await callback_query.answer("❌ User not found", show_alert=True)
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            await callback_query.answer("❌ Barber not found", show_alert=True)
            return

        await redis_pool.set(f"user:{user.telegram_id}:last_action", "barber_service")

        # find existing BarberService
        bs = (
            await session.execute(
                select(BarberService).where(
                    BarberService.barber_id == barber.id,
                    BarberService.service_id == service_id,
                )
            )
        ).scalar_one_or_none()

        if bs:
            bs.is_active = not bs.is_active  # ✅ toggle status instead of delete/add
        else:
            session.add(BarberService(
                barber_id=barber.id,
                service_id=service_id,
                price=0,
                is_active=True
            ))

        await session.commit()

        # refresh lists for keyboard
        all_services = (await session.execute(
            select(Service).where(Service.disabled.is_(False))
        )).scalars().all()

        barber_services = (
            await session.execute(
                select(BarberService).where(BarberService.barber_id == barber.id)
            )
        ).scalars().all()

        lang = user.lang or "uz"
        await callback_query.message.edit_reply_markup(
            reply_markup=service_selection_inline_keyboard(all_services, barber_services, lang)
        )
        await callback_query.answer("✅ Service updated")


@barber_service.callback_query(F.data.startswith("service_"))
async def handle_service_click(callback_query: CallbackQuery):
    service_id = int(callback_query.data.split("_")[1])
    redis_pool = callback_query.bot.redis

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == callback_query.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await callback_query.answer("❌ User not found", show_alert=True)
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            await callback_query.answer("❌ Barber not found", show_alert=True)
            return

        # store selected service on Barber
        barber.selected_service = service_id
        await session.commit()

        await redis_pool.set(f"user:{user.telegram_id}:last_action", "service_profile")

        lang = user.lang or "uz"

    await callback_query.message.answer(
        "Quyidagi amallardan birini tanlang:" if lang == "uz" else "Выберите действие:",
        reply_markup=price_action_keyboard(lang),
    )
    await callback_query.answer()


@barber_service.message(F.text.in_(["✏️ Narxni belgilash", "✏️ Установить цену"]))
async def set_price_prompt(message: Message, state: FSMContext):
    lang_guess = "uz" if message.text.startswith("✏️ N") else "ru"
    prompt = "Narxni kiriting (so'mda):" if lang_guess == "uz" else "Введите цену (в сумах):"
    await message.answer(prompt)
    await state.set_state(BarberServiceStates.waiting_for_price)


@barber_service.message(BarberServiceStates.waiting_for_price)
async def receive_price(message: Message, state: FSMContext):
    redis_pool = message.bot.redis
    # validate price
    try:
        price = int(message.text.strip())
        if price <= 0:
            raise ValueError
    except Exception:
        # fall back to user lang if possible
        async with AsyncSessionLocal() as session:
            user = (
                await session.execute(
                    select(User).where(User.telegram_id == message.from_user.id)
                )
            ).scalar_one_or_none()
            lang = (user.lang if user and user.lang else "uz")
        await message.answer(
            "Iltimos, to‘g‘ri narx kiriting." if lang == "uz" else "Пожалуйста, введите правильную цену."
        )
        return

    async with AsyncSessionLocal() as session:
        # user + barber
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await message.answer("❌ User not found.")
            await state.clear()
            return
        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            await message.answer("❌ Barber not found.")
            await state.clear()
            return

        service_id = barber.selected_service
        if not service_id:
            await message.answer(
                "Xizmat topilmadi. Qaytadan urinib ko‘ring." if (
                                                                        user.lang or "uz") == "uz" else "Услуга не найдена. Попробуйте снова."
            )
            await state.clear()
            return

        # find BarberService
        bs = (
            await session.execute(
                select(BarberService).where(
                    and_(
                        BarberService.barber_id == barber.id,
                        BarberService.service_id == int(service_id),
                    )
                )
            )
        ).scalar_one_or_none()
        if not bs:
            await message.answer(
                "Xizmat bilan bog‘liq muammo yuz berdi." if (
                                                                    user.lang or "uz") == "uz" else "Произошла ошибка с услугой."
            )
            await state.clear()
            return

        bs.price = price
        await session.commit()

        # refresh services list
        services = (
            await session.execute(
                select(BarberService).where(BarberService.barber_id == barber.id)
            )
        ).scalars().all()

        await message.answer(
            "Narx saqlandi ✅" if (user.lang or "uz") == "uz" else "Цена сохранена ✅",
            reply_markup=barber_services_keyboard(services, user.lang or "uz"),
        )
        await state.clear()
        await redis_pool.delete(f"user:{user.telegram_id}:service_id")


@barber_service.message(F.text.in_(["🗑 Xizmatni o'chirish", "🗑 Удалить услугу"]))
async def remove_service(message: Message, state: FSMContext):
    redis_pool = message.bot.redis

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await message.answer("❌ User not found. Please restart /start.")
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            await message.answer("❌ Barber profile not found.")
            return

        service_id = barber.selected_service
        if not service_id:
            await message.answer("❌ Xizmat tanlanmagan." if (user.lang or "uz") == "uz" else "❌ Услуга не выбрана.")
            return

        bs = (
            await session.execute(
                select(BarberService).where(
                    and_(
                        BarberService.barber_id == barber.id,
                        BarberService.service_id == service_id,
                    )
                )
            )
        ).scalar_one_or_none()

        if bs:
            await session.delete(bs)
            await session.commit()

        # refresh list
        services = (
            await session.execute(
                select(BarberService).where(BarberService.barber_id == barber.id)
            )
        ).scalars().all()

        lang = user.lang or "uz"
        await message.answer(
            "Xizmat o‘chirildi ✅" if lang == "uz" else "Услуга удалена ✅",
            reply_markup=barber_service_menu_keyboard(lang),
        )
        await state.clear()

        if not services:
            await message.answer(
                "Siz hali xizmat qo‘shmagansiz." if lang == "uz" else "У вас пока нет услуг.",
                reply_markup=barber_service_menu_keyboard(lang),
            )
            return

        await message.answer(
            "Xizmatlaringiz ro'yxati:" if lang == "uz" else "Ваши услуги:",
            reply_markup=barber_services_keyboard(services, lang),
        )
        await redis_pool.delete(f"user:{user.telegram_id}:service_id")


@barber_service.message(F.text.in_(["⏱ Davomiylikni belgilash", "⏱ Установить длительность"]))
async def ask_service_id(message: Message, state: FSMContext):
    await state.clear()

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await message.answer("❌ User not found.")
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            await message.answer(
                "❌ Siz ro‘yxatdan o‘tmagansiz." if (user.lang or "uz") == "uz" else "❌ Вы не зарегистрированы.")
            return

        text = (
            "⏱ Davomiylikni daqiqalarda kiriting (masalan: 45)"
            if (user.lang or "uz") == "uz"
            else "⏱ Введите продолжительность в минутах (например: 45)"
        )
        await message.answer(text)

    await state.set_state(DurationStates.waiting_for_duration)


@barber_service.message(DurationStates.waiting_for_duration)
async def receive_duration(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await message.answer("❌ User not found.")
            return

        barber = (
            await session.execute(
                select(Barber).where(Barber.user_id == user.id, Barber.login == user.platform_login)
            )
        ).scalar_one_or_none()
        if not barber:
            await message.answer("❌ Barber not found.")
            return

        service_id = barber.selected_service
        if not service_id:
            await message.answer(
                "❌ Xizmat tanlanmagan." if (user.lang or "uz") == "uz" else "❌ Услуга не выбрана."
            )
            return

        # validate input
        try:
            duration = int(message.text.strip())
            if duration <= 0:
                raise ValueError
        except Exception:
            await message.answer(
                "❌ Davomiylik faqat musbat son bo‘lishi kerak."
                if (user.lang or "uz") == "uz"
                else "❌ Длительность должна быть положительным числом."
            )
            return

        # find BarberService
        bs = (
            await session.execute(
                select(BarberService).where(
                    and_(
                        BarberService.barber_id == barber.id,
                        BarberService.service_id == service_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if not bs:
            await message.answer("❌ Xizmat topilmadi." if (user.lang or "uz") == "uz" else "❌ Услуга не найдена.")
            return

        bs.duration = duration
        await session.commit()

        # refresh list
        services = (
            await session.execute(
                select(BarberService).where(BarberService.barber_id == barber.id)
            )
        ).scalars().all()

        text = (
            "✅ Xizmat davomiyligi belgilandi." if (user.lang or "uz") == "uz" else "✅ Длительность услуги установлена."
        )
        await message.answer(text, reply_markup=barber_services_keyboard(services, user.lang or "uz"))
        await state.clear()
