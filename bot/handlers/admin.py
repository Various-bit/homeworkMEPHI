from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import Config
from bot.constants import META_SUBJECT_NAME
from bot.database import requests as db
from bot.filters.roles import IsAdmin
from bot.keyboards.reply import main_menu, cancel_kb, skip_or_cancel_kb
from bot.keyboards.inline import (
    back_to_homework_kb,
    confirm_delete_homework_kb,
    confirm_homework_kb,
    dates_kb,
    homework_list_kb,
    subjects_kb,
)
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
    await state.set_state(AddHomework.description)

    if subject["name"] == META_SUBJECT_NAME:
        await state.update_data(shift_meta_queue=True)
        await callback.message.edit_text(
            f"Предмет: «{subject['name']}»\n"
            "⚠️ После сохранения задания очередь сдвинется: очередь на "
            "Занятие 1 удалится, 2→1, 3→2, откроется новое Занятие 3."
        )
    else:
        await callback.message.edit_text(f"Предмет: «{subject['name']}»")

    await callback.message.answer("Теперь введите текст задания:", reply_markup=cancel_kb())
    await callback.answer()


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
    if data.get("shift_meta_queue"):
        await db.shift_meta_sessions(data["subject_id"])
        text += "\n♻️ Очередь по темам сдвинута: Занятие 1 закрыто, 2→1, 3→2, открыто новое Занятие 3."

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


@router.callback_query(F.data.startswith("delhw:"))
async def ask_delete_homework(callback: CallbackQuery) -> None:
    homework_id = int(callback.data.removeprefix("delhw:"))
    item = await db.get_homework(homework_id)
    if item is None:
        await callback.answer("Это ДЗ уже удалено.", show_alert=True)
        return

    text = (
        "Удалить это задание без возможности восстановить?\n\n"
        f"📘 <b>{item['subject_name']}</b> · {item['created_date']}\n{item['description']}"
    )
    await callback.message.edit_text(text, reply_markup=confirm_delete_homework_kb(homework_id))
    await callback.answer()


@router.callback_query(F.data.startswith("delhw_yes:"))
async def do_delete_homework(callback: CallbackQuery) -> None:
    homework_id = int(callback.data.removeprefix("delhw_yes:"))
    item = await db.get_homework(homework_id)
    if item is None:
        await callback.answer("Это ДЗ уже удалено.", show_alert=True)
        return

    await db.delete_homework(homework_id)

    items = await db.get_homework_by_subject_date(item["subject_id"], item["created_date"])
    if items:
        await callback.message.edit_text(
            f"🗑 Удалено.\n\n«{item['subject_name']}» · {item['created_date']}:",
            reply_markup=homework_list_kb(item["subject_id"], item["created_date"], items),
        )
    else:
        dates = await db.get_dates_for_subject(item["subject_id"])
        if dates:
            await callback.message.edit_text(
                f"🗑 Удалено. На {item['created_date']} больше нет заданий по «{item['subject_name']}».",
                reply_markup=dates_kb(item["subject_id"], dates),
            )
        else:
            await callback.message.edit_text(
                f"🗑 Удалено. По «{item['subject_name']}» пока нет заданий."
            )
    await callback.answer("Удалено")


@router.callback_query(F.data.startswith("delhw_no:"))
async def cancel_delete_homework(callback: CallbackQuery) -> None:
    homework_id = int(callback.data.removeprefix("delhw_no:"))
    item = await db.get_homework(homework_id)
    if item is None:
        await callback.answer("Это ДЗ уже удалено.", show_alert=True)
        return

    await callback.message.edit_text(
        "Что дальше?",
        reply_markup=back_to_homework_kb(
            item["subject_id"], item["created_date"], homework_id=homework_id, can_delete=True
        ),
    )
    await callback.answer()
