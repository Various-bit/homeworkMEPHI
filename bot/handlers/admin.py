from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import Config
from bot.constants import META_SUBJECT_NAME
from bot.database import requests as db
from bot.filters.roles import IsAdmin
from bot.keyboards.reply import main_menu, cancel_kb, skip_or_cancel_kb
from bot.keyboards.inline import confirm_homework_kb, subjects_kb
from bot.states.states import AddHomework

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text == "➕ Добавить ДЗ")
async def start_add_homework(message: Message, state: FSMContext) -> None:
    subjects = await db.list_subjects()
    await state.set_state(AddHomework.choose_subject)
    await message.answer(
        "Выберите предмет, по которому добавляете задание:",
        reply_markup=subjects_kb(subjects, prefix="addsubj"),
    )


@router.callback_query(AddHomework.choose_subject, F.data.startswith("addsubj:"))
async def process_subject(callback: CallbackQuery, state: FSMContext) -> None:
    subject_id = int(callback.data.removeprefix("addsubj:"))
    subject = await db.get_subject(subject_id)
    if subject is None:
        await callback.answer("Предмет не найден.", show_alert=True)
        return

    await state.update_data(subject_id=subject_id, subject_name=subject["name"])
    await callback.message.edit_text(f"Предмет: «{subject['name']}»")

    if subject["name"] == META_SUBJECT_NAME:
        await state.set_state(AddHomework.topics_count)
        await callback.message.answer(
            "Сколько тем в этом задании? Пришлите число.\n"
            "⚠️ Это заменит текущий список тем и обнулит очередь по ним.",
            reply_markup=cancel_kb(),
        )
    else:
        await state.set_state(AddHomework.description)
        await callback.message.answer("Теперь введите текст задания:", reply_markup=cancel_kb())
    await callback.answer()


@router.message(AddHomework.topics_count)
async def process_topics_count(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit() or int(message.text.strip()) < 1:
        await message.answer("Пришлите положительное число тем.")
        return

    await state.update_data(topics_count=int(message.text.strip()))
    await state.set_state(AddHomework.description)
    await message.answer("Теперь введите текст задания:", reply_markup=cancel_kb())


@router.message(AddHomework.description)
async def process_description(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Пришлите текст задания сообщением.")
        return

    await state.update_data(description=message.text.strip())
    await state.set_state(AddHomework.attachment)
    await message.answer(
        "Можно приложить файл или фото к заданию, либо пропустить этот шаг.",
        reply_markup=skip_or_cancel_kb(),
    )


@router.message(AddHomework.attachment, F.text == "⏭ Без вложения")
async def skip_attachment(message: Message, state: FSMContext) -> None:
    await state.update_data(file_id=None, file_type=None)
    await show_confirmation(message, state)


@router.message(AddHomework.attachment, F.photo)
async def attach_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(file_id=message.photo[-1].file_id, file_type="photo")
    await show_confirmation(message, state)


@router.message(AddHomework.attachment, F.document)
async def attach_document(message: Message, state: FSMContext) -> None:
    await state.update_data(file_id=message.document.file_id, file_type="document")
    await show_confirmation(message, state)


@router.message(AddHomework.attachment)
async def attachment_wrong_type(message: Message) -> None:
    await message.answer("Пришлите фото, документ или нажмите «⏭ Без вложения».")


async def show_confirmation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(AddHomework.confirm)

    text = f"📘 <b>{data['subject_name']}</b>\n\n{data['description']}"
    if data.get("file_type") == "photo":
        await message.answer_photo(data["file_id"], caption=text, reply_markup=confirm_homework_kb())
    elif data.get("file_type") == "document":
        await message.answer_document(data["file_id"], caption=text, reply_markup=confirm_homework_kb())
    else:
        await message.answer(text, reply_markup=confirm_homework_kb())


@router.callback_query(AddHomework.confirm, F.data == "confirm_hw")
async def confirm_homework(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    data = await state.get_data()
    await db.add_homework(
        subject_id=data["subject_id"],
        description=data["description"],
        added_by=callback.from_user.id,
        added_by_name=callback.from_user.full_name,
        file_id=data.get("file_id"),
        file_type=data.get("file_type"),
    )

    text = "✅ Задание сохранено."
    if data.get("topics_count"):
        await db.reset_meta_topics(data["subject_id"], data["topics_count"])
        text += f"\n♻️ Создано тем: {data['topics_count']}, очередь по ним обнулена."

    await state.clear()

    is_super = callback.from_user.id in config.super_admin_ids
    await callback.message.answer(
        text,
        reply_markup=main_menu(is_admin=True, is_super_admin=is_super),
    )
    await callback.answer()


@router.callback_query(AddHomework.confirm, F.data == "cancel_hw")
async def cancel_homework(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    await state.clear()
    is_super = callback.from_user.id in config.super_admin_ids
    await callback.message.answer(
        "Отменено.", reply_markup=main_menu(is_admin=True, is_super_admin=is_super)
    )
    await callback.answer()
