from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
from .utils import _wd_names, _t, _fmt_d
from datetime import date


def barber_services_keyboard(services: List, lang: str = "uz") -> InlineKeyboardMarkup:
    service_buttons = []

    for bs in services:
        # Get service name
        if lang == "ru":
            name = getattr(bs.service, "name_ru", None) or "Название услуги"
            price = f"{bs.price} сум" if bs.price else "Цена не указана"
            duration = f"{bs.duration} мин" if bs.duration else "Время не указано"
        else:
            name = getattr(bs.service, "name_uz", None) or "Nomaʼlum xizmat"
            price = f"{bs.price} so'm" if bs.price else "Narx belgilanmagan"
            duration = f"{bs.duration} daqiqa" if bs.duration else "Davomiylik belgilanmagan"

        # Show name — price — duration
        button_text = f"{name} — {price} — {duration}"
        callback_data = f"service_{bs.service.id}"

        service_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    return InlineKeyboardMarkup(inline_keyboard=service_buttons)


def barber_service_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    if lang == "ru":
        add_service = "➕ Добавить услугу"
        back = "⬅️ Назад"
    else:
        add_service = "➕ Xizmat qo‘shish"
        back = "⬅️ Orqaga"

    keyboard = [
        [KeyboardButton(text=add_service),
         KeyboardButton(text=back)]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def service_selection_inline_keyboard(all_services, barber_services, lang="uz"):
    active_ids = {bs.service_id for bs in barber_services if bs.is_active}
    keyboard = []

    for service in all_services:
        is_active = service.id in active_ids
        mark = "✅" if is_active else "❌"
        name = getattr(service, f"name_{lang}", None) or (
            service.name_uz if lang == "uz" else service.name_ru
        )
        button = InlineKeyboardButton(
            text=f"{mark} {name}",
            callback_data=f"toggle_service:{service.id}"
        )
        keyboard.append([button])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def price_action_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    if lang == "ru":
        buttons = [
            [
                KeyboardButton(text="✏️ Установить цену"),
                KeyboardButton(text="⏱ Установить длительность"),
            ],
            [
                KeyboardButton(text="🗑 Удалить услугу"),
                KeyboardButton(text="⬅️ Назад")
            ],
        ]
    else:
        buttons = [
            [
                KeyboardButton(text="✏️ Narxni belgilash"),
                KeyboardButton(text="⏱ Davomiylikni belgilash"),
            ],
            [
                KeyboardButton(text="🗑 Xizmatni o'chirish"),
                KeyboardButton(text="⬅️ Orqaga")
            ],
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def barber_info_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    lang = lang.lower()

    if lang == "ru":
        buttons = [
            [KeyboardButton(text="📄 Резюме"), KeyboardButton(text="🖼 Фото профиля")],
            [KeyboardButton(text="📅 Рабочие дни"), KeyboardButton(text="🕒 Время работы")],
            [KeyboardButton(text="📍 Локация"), KeyboardButton(text="⬅️ Назад")],

        ]
    else:  # default to Uzbek
        buttons = [
            [KeyboardButton(text="📄 Rezyume"), KeyboardButton(text="🖼 Profil rasmi")],
            [KeyboardButton(text="📅 Ish kunlari"), KeyboardButton(text="🕒 Ish vaqti")],
            [KeyboardButton(text="📍 Manzil"), KeyboardButton(text="⬅️ Orqaga")],

        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def resume_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    if lang == "ru":
        buttons = [
            [KeyboardButton(text="✏️ Редактировать резюме"), KeyboardButton(text="⬅️ Назад")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="✏️ Rezyumeni tahrirlash"), KeyboardButton(text="⬅️ Orqaga")]
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def profile_image_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    if lang == "ru":
        buttons = [
            [KeyboardButton(text="🖼 Изменить фото профиля"),
             KeyboardButton(text="⬅️ Назад")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="🖼 Profil rasmini o‘zgartirish"),
             KeyboardButton(text="⬅️ Orqaga")]
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def working_time_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    lang = lang.lower()
    if lang == "ru":
        buttons = [
            [KeyboardButton(text="⏱ Установить время"),
             KeyboardButton(text="⬅️ Назад")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="⏱ Vaqt belgilash"),
             KeyboardButton(text="⬅️ Orqaga")]
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def barber_map_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    lang = lang.lower()

    if lang == "ru":
        buttons = [
            [KeyboardButton(text="✏️ Изменить локацию"), KeyboardButton(text="✏️ Изменить адрес")],
            [KeyboardButton(text="✏️ Изменить название салона"), KeyboardButton(text="⬅️ Назад")]
        ]
    else:  # Uzbek default
        buttons = [
            [KeyboardButton(text="✏️ Joylashuvni o'zgartirish"), KeyboardButton(text="✏️ Manzilni o'zgartirish")],
            [KeyboardButton(text="✏️ Salon nomini o'zgartirish"), KeyboardButton(text="⬅️ Orqaga")]
        ]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def location_request_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    lang = lang.lower()

    if lang == "ru":
        buttons = [
            [KeyboardButton(text="📍 Отправить локацию", request_location=True),
             KeyboardButton(text="⬅️ Назад")]
        ]
    else:  # Default to Uzbek
        buttons = [
            [KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True),
             KeyboardButton(text="⬅️ Orqaga")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def barber_working_days_keyboard(days, lang: str = "uz") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for day in days:
        name = day.name_uz if lang == "uz" else day.name_ru
        status = "✅" if getattr(day, "is_working", False) else "❌"
        builder.button(
            text=f"{status} {name}",
            callback_data=f"toggle_day:{day.id}"
        )

    builder.adjust(2)

    return builder.as_markup()


def request_row_kb(req_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    ru = (lang or "").lower().startswith("ru")

    text_accept = "✅ Принять" if ru else "✅ Qabul qilish"
    text_deny = "❌ Отклонить" if ru else "❌ Rad etish"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=text_accept, callback_data=f"req:{req_id}:accept"),
            InlineKeyboardButton(text=text_deny, callback_data=f"req:{req_id}:deny"),
        ]
    ])
    return kb


def build_profile_button(client_user, lang: str = "uz") -> Optional[InlineKeyboardButton]:
    # Python 3.9-friendly: remove the "|" and use Optional[InlineKeyboardButton] if needed
    ru = (lang or "").lower().startswith("ru")
    text = "🔗 Профиль в Telegram" if ru else "🔗 Telegram profili"

    username = getattr(client_user, "username", None)
    tg_id = getattr(client_user, "telegram_id", None)

    if username:
        url = f"https://t.me/{username.lstrip('@')}"  # official profile link
        return InlineKeyboardButton(text=text, url=url)
    elif tg_id:
        # Fallback – deep link (works in most clients, not a public profile link)
        return InlineKeyboardButton(text=text, url=f"tg://user?id={tg_id}")
    return None


def kb_week_days(days: List[date], working_map: dict, lang: str) -> InlineKeyboardMarkup:
    """
    working_map: { day_date -> bool } (True if working)
    """
    wd_names = _wd_names(lang)
    rows = []
    for d in days:
        idx = d.weekday()  # 0..6
        label = wd_names[idx]
        mark = "✅" if working_map.get(d, False) else "❌"
        btn = InlineKeyboardButton(
            text=f"{mark} {label} • {_fmt_d(d)}",
            callback_data=f"sched:day:{_fmt_d(d)}:p1"
        )
        rows.append([btn])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_requests_paged(selected_day: date, page: int, max_page: int, lang: str) -> InlineKeyboardMarkup:
    prev_btn = InlineKeyboardButton(text="◀️", callback_data=f"sched:day:{_fmt_d(selected_day)}:p{max(1, page - 1)}")
    page_btn = InlineKeyboardButton(text=_t(lang, f"Sahifa {page}/{max_page}", f"Стр. {page}/{max_page}"),
                                    callback_data="sched:nop")
    next_btn = InlineKeyboardButton(text="▶️",
                                    callback_data=f"sched:day:{_fmt_d(selected_day)}:p{min(max_page, page + 1)}")
    back_btn = InlineKeyboardButton(text=_t(lang, "⬅️ Haftaga qaytish", "⬅️ К неделе"), callback_data="sched:back")

    rows = []
    if max_page > 1:
        rows.append([prev_btn, page_btn, next_btn])
    rows.append([back_btn])
    return InlineKeyboardMarkup(inline_keyboard=rows)
