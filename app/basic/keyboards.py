from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

language_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇺🇿 UZ"), KeyboardButton(text="🇷🇺 RU")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


def get_login_keyboard(lang: str) -> ReplyKeyboardMarkup:
    text = {
        "uz": "🔐 Kirish",
        "ru": "🔐 Войти"
    }.get(lang, "🔐 Kirish")  # fallback to Uzbek

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)]],
        resize_keyboard=True
    )


def user_role_keyboard(lang: str) -> ReplyKeyboardMarkup:
    texts = {
        "uz": ["👤 Mijoz", "✂️ Sartarosh"],
        "ru": ["👤 Клиент", "✂️ Парикмахер"],
    }
    client_text, barber_text = texts.get(lang, ["👤 Mijoz", "✂️ Sartarosh"])

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=client_text), KeyboardButton(text=barber_text)]
        ],
        resize_keyboard=True
    )


def back_keyboard(lang: str) -> ReplyKeyboardMarkup:
    texts = {
        "uz": "⬅️ Orqaga",
        "ru": "⬅️ Назад"
    }

    back_text = texts.get(lang, "⬅️ Orqaga")  # fallback to Uzbek

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=back_text)]
        ],
        resize_keyboard=True
    )


def barber_main_menu(lang: str) -> ReplyKeyboardMarkup:
    texts = {
        "uz": [
            "✂️ Mening xizmatlarim",
            "📅 Jadvalim",
            "📊 Mening ballarim",
            "📨 So‘rovlar",
            "ℹ️ Ma’lumot",
            "🌐 Tilni o‘zgartirish",
            "🔐 Chiqish"
        ],
        "ru": [
            "✂️ Мои услуги",
            "📅 Мое расписание",
            "📊 Мои баллы",
            "📨 Запросы",
            "ℹ️ Информация",
            "🌐 Сменить язык",
            "🔐 Выход"
        ]
    }

    buttons = texts.get(lang, texts["uz"])

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buttons[0]), KeyboardButton(text=buttons[1]), KeyboardButton(text=buttons[3])],
            [KeyboardButton(text=buttons[2]), KeyboardButton(text=buttons[4]), KeyboardButton(text=buttons[5])]
            # [KeyboardButton(text=buttons[6])]
        ],
        resize_keyboard=True
    )


def client_main_menu(lang: str) -> ReplyKeyboardMarkup:
    if lang == "ru":
        send_location_text = "📍 Отправить мою локацию"
        barbers_text = "✂️ Барберы"
        my_barbers_text = "🪮 Мои барберы"
        back_text = "🔐 Выход"
        change_lang_text = "🌐 Сменить язык"
    else:  # default uz
        send_location_text = "📍 Lokatsiyamni yuborish"
        barbers_text = "✂️ Barberlar"
        my_barbers_text = "🪮 Mening barberlarim"
        back_text = "🔐 Chiqish"
        change_lang_text = "🌐 Tilni o‘zgartirish"

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=send_location_text), KeyboardButton(text=barbers_text)],
            [KeyboardButton(text=my_barbers_text), KeyboardButton(text=change_lang_text)]
            # [KeyboardButton(text=back_text)]
        ],
        resize_keyboard=True
    )

    return keyboard
