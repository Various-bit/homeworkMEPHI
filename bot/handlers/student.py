from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from bot.config import Config
from bot.database import requests as db
from bot.keyboards.inline import subjects_kb, dates_kb, homework_list_kb, back_to_homework_kb

router = Router()


@router.message(F.text == "📚 Посмотреть ДЗ")
async def view_homework(message: Message) -> None:
    subjects = await db.get_subjects_with_homework()
    if not subjects:
        await message.answer("Пока нет ни одного домашнего задания.")
        return

    await message.answer("Выберите предмет:", reply_markup=subjects_kb(subjects, prefix="subj"))


@router.callback_query(F.data == "back_subjects")
async def back_to_subjects(callback: CallbackQuery) -> None:
    subjects = await db.get_subjects_with_homework()
    if not subjects:
        await callback.message.edit_text("Пока нет ни одного домашнего задания.")
        await callback.answer()
        return

    await callback.message.edit_text("Выберите предмет:", reply_markup=subjects_kb(subjects, prefix="subj"))
    await callback.answer()


@router.callback_query(F.data.startswith("subj:"))
async def show_subject_dates(callback: CallbackQuery) -> None:
    subject_id = int(callback.data.removeprefix("subj:"))
    subject = await db.get_subject(subject_id)
    dates = await db.get_dates_for_subject(subject_id)

    if subject is None:
        await callback.answer("Предмет не найден.", show_alert=True)
        return

    if not dates:
        await callback.message.edit_text(
            f"По предмету «{subject['name']}» пока нет ДЗ.",
            reply_markup=subjects_kb(await db.get_subjects_with_homework(), prefix="subj"),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"«{subject['name']}»\nВыберите дату добавления ДЗ:",
        reply_markup=dates_kb(subject_id, dates),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("date:"))
async def show_date(callback: CallbackQuery) -> None:
    _, subject_id_raw, date = callback.data.split(":", maxsplit=2)
    subject_id = int(subject_id_raw)
    subject = await db.get_subject(subject_id)
    items = await db.get_homework_by_subject_date(subject_id, date)

    if not items:
        await callback.message.edit_text(
            "На эту дату заданий не найдено.",
            reply_markup=dates_kb(subject_id, await db.get_dates_for_subject(subject_id)),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"«{subject['name']}» · {date}:",
        reply_markup=homework_list_kb(subject_id, date, items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("hw:"))
async def show_homework(callback: CallbackQuery, config: Config) -> None:
    homework_id = int(callback.data.removeprefix("hw:"))
    item = await db.get_homework(homework_id)

    if item is None:
        await callback.answer("Это ДЗ уже удалено.", show_alert=True)
        return

    is_admin = callback.from_user.id in config.super_admin_ids or await db.is_admin(callback.from_user.id)

    caption = (
        f"📘 <b>{item['subject_name']}</b>\n\n"
        f"{item['description']}\n\n"
        f"Добавил: {item['added_by_name']}\n"
        f"Дата: {item['created_date']}"
    )

    if item["file_id"] and item["file_type"] == "photo":
        await callback.message.answer_photo(item["file_id"], caption=caption)
    elif item["file_id"] and item["file_type"] == "document":
        await callback.message.answer_document(item["file_id"], caption=caption)
    else:
        await callback.message.answer(caption)

    await callback.message.answer(
        "Что дальше?",
        reply_markup=back_to_homework_kb(
            item["subject_id"], item["created_date"], homework_id=item["id"], can_delete=is_admin
        ),
    )
    await callback.answer()
