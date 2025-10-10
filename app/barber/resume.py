from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from sqlalchemy import select
from app.barber.models import Barber
from app.user.models import User
from .keyboards import resume_keyboard
from app.states import FileUpload
from app.db import AsyncSessionLocal
import os

barber_resume = Router()


@barber_resume.message(F.text.in_(['📄 Rezyume', '📄 Резюме']))
async def show_resume(message: Message):
    redis_pool = message.bot.redis
    async with AsyncSessionLocal() as session:
        # load user + barber
        user_obj = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user_obj:
            await message.answer("❌ Foydalanuvchi topilmadi." if message.from_user.language_code == "uz"
                                 else "❌ Пользователь не найден.")
            return

        barber_obj = (
            await session.execute(
                select(Barber).where(Barber.user_id == user_obj.id, Barber.login == user_obj.platform_login)
            )
        ).scalar_one_or_none()
        lang = user_obj.lang or "uz"
        text = "Rezyume:" if lang == "uz" else "Резюме:"

        await redis_pool.set(f"user:{user_obj.telegram_id}:last_action", "barber_resume")

        if barber_obj and barber_obj.resume:
            resume_path = os.path.abspath(barber_obj.resume)
            if os.path.isfile(resume_path):
                try:
                    file = FSInputFile(resume_path)
                    await message.answer_document(file, caption=text, reply_markup=resume_keyboard(lang))
                except Exception:
                    await message.answer(
                        f"{text}\n❗ Faylni yuborib bo‘lmadi." if lang == "uz"
                        else f"{text}\n❗ Не удалось отправить файл.",
                        reply_markup=resume_keyboard(lang)
                    )
            else:
                await message.answer(
                    f"{text}\n❗ Rezyume fayli topilmadi." if lang == "uz"
                    else f"{text}\n❗ Файл резюме не найден.",
                    reply_markup=resume_keyboard(lang)
                )
        else:
            await message.answer(
                f"{text}\n❗ Rezyume topilmadi." if lang == "uz"
                else f"{text}\n❗ Резюме не найдено.",
                reply_markup=resume_keyboard(lang)
            )


@barber_resume.message(F.text.in_(['✏️ Rezyumeni tahrirlash', '✏️ Редактировать резюме']))
async def start_upload_resume(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user_obj = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        lang = user_obj.lang or "uz" if user_obj else "uz"

    if lang == "ru":
        msg = (
            "📄 Пожалуйста, отправьте ваш резюме-файл.\n\n"
            "✅ Поддерживаемые форматы: PDF, DOC, DOCX\n"
            "⛔️ Нельзя отправлять изображения или другие типы файлов.\n\n"
            "Максимальный размер — до 5MB."
        )
    else:
        msg = (
            "📄 Iltimos, rezyume faylingizni yuboring.\n\n"
            "✅ Qo‘llab-quvvatlanadigan formatlar: PDF, DOC, DOCX\n"
            "⛔️ Rasm yoki boshqa turdagi fayllar yuborilmasin.\n\n"
            "Maksimal hajm — 5MB gacha."
        )

    await message.answer(msg)
    await state.set_state(FileUpload.waiting_for_file)


@barber_resume.message(FileUpload.waiting_for_file, F.document)
async def process_resume_file(message: Message, state: FSMContext, bot: Bot):
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    UPLOAD_FOLDER = "static/resumes/"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    document = message.document

    # ✅ Check MIME type
    if document.mime_type not in [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        await message.answer(
            "❗ Faqat PDF yoki DOC fayl yuboring!" if message.from_user.language_code == "uz"
            else "❗ Отправьте только PDF или DOC файл!"
        )
        return

    # ✅ Check file size
    if document.file_size > MAX_FILE_SIZE:
        await message.answer(
            "❗ Fayl hajmi 5MB dan oshmasligi kerak!" if message.from_user.language_code == "uz"
            else "❗ Размер файла не должен превышать 5MB!"
        )
        return

    # ✅ Download file
    file_info = await bot.get_file(document.file_id)
    file_path = os.path.join(UPLOAD_FOLDER, f"{message.from_user.id}_{document.file_name}")
    downloaded_file = await bot.download_file(file_info.file_path)

    with open(file_path, "wb") as f:
        f.write(downloaded_file.read())

    # ✅ Save to DB
    async with AsyncSessionLocal() as session:
        user_obj = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if not user_obj:
            await message.answer("❌ Foydalanuvchi topilmadi." if message.from_user.language_code == "uz"
                                 else "❌ Пользователь не найден.")
            return

        barber_obj = (
            await session.execute(
                select(Barber).where(Barber.user_id == user_obj.id, Barber.login == user_obj.platform_login)
            )
        ).scalar_one_or_none()
        if barber_obj:
            barber_obj.resume = file_path
            await session.commit()

        lang = user_obj.lang or "uz"

    # ✅ Notify user
    msg = "✅ Rezyume muvaffaqiyatli yuklandi!" if lang == "uz" else "✅ Резюме успешно загружено!"
    await message.answer(msg)

    caption = "Rezyume:" if lang == "uz" else "Резюме:"
    file = FSInputFile(file_path)
    await message.answer_document(file, caption=caption, reply_markup=resume_keyboard(lang))

    await state.clear()
