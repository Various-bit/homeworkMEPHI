from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.constants import META_SUBJECT_NAME
from bot.database import requests as db
from bot.keyboards.inline import meta_cell_detail_kb, meta_sessions_overview_kb, meta_topics_for_session_kb

router = Router()


async def _sessions_screen(subject_id: int) -> tuple[str, InlineKeyboardMarkup]:
    totals = await db.get_session_totals(subject_id)
    return f"Очередь на «{META_SUBJECT_NAME}»\nВыберите занятие:", meta_sessions_overview_kb(totals)


async def _topics_screen(subject_id: int, session_position: int) -> tuple[str, InlineKeyboardMarkup]:
    topics = await db.get_topics_for_session(subject_id, session_position)
    text = f"Занятие {session_position}\nВыберите тему:"
    return text, meta_topics_for_session_kb(session_position, topics)


@router.message(F.text == "📋 Очередь на метаязыки")
async def show_queue_menu(message: Message) -> None:
    subject = await db.get_subject_by_name(META_SUBJECT_NAME)
    if subject is None:
        await message.answer("Предмет не найден.")
        return

    text, kb = await _sessions_screen(subject["id"])

    entries = await db.get_user_meta_queue_entries(subject["id"], message.from_user.id)
    if entries:
        lines = []
        for entry in entries:
            position = await db.get_queue_position(entry["topic_id"], entry["session_position"], message.from_user.id)
            lines.append(f"Занятие {entry['session_position']} — Тема {entry['number']} (вы {position}-й)")
        text = "Вы записаны:\n" + "\n".join(lines) + "\n\n" + text

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "mback")
async def back_to_sessions(callback: CallbackQuery) -> None:
    subject = await db.get_subject_by_name(META_SUBJECT_NAME)
    text, kb = await _sessions_screen(subject["id"])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("msession:"))
async def open_session(callback: CallbackQuery) -> None:
    session_position = int(callback.data.removeprefix("msession:"))
    subject = await db.get_subject_by_name(META_SUBJECT_NAME)

    text, kb = await _topics_screen(subject["id"], session_position)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("mtopic:"))
async def open_topic(callback: CallbackQuery) -> None:
    _, position_raw, topic_id_raw = callback.data.split(":")
    session_position, topic_id = int(position_raw), int(topic_id_raw)

    topic = await db.get_meta_topic(topic_id)
    if topic is None:
        await callback.answer("Тема не найдена.", show_alert=True)
        return

    user_id = callback.from_user.id
    entry = await db.get_user_entry_for_session(topic["subject_id"], session_position, user_id)

    if entry and entry["topic_id"] != topic_id:
        await callback.answer(
            f"На Занятие {session_position} вы уже записаны на Тему {entry['number']}. "
            "Сначала выйдите из неё.",
            show_alert=True,
        )
        return

    if not entry:
        await db.join_meta_queue(topic_id, session_position, user_id, callback.from_user.full_name)

    position = await db.get_queue_position(topic_id, session_position, user_id)
    text = f"Занятие {session_position}, Тема {topic['number']}\nВы в очереди, ваша позиция: {position}."
    await callback.message.edit_text(text, reply_markup=meta_cell_detail_kb(session_position, joined=True))
    await callback.answer()


@router.callback_query(F.data.startswith("mleave:"))
async def leave_queue(callback: CallbackQuery) -> None:
    session_position = int(callback.data.removeprefix("mleave:"))
    subject = await db.get_subject_by_name(META_SUBJECT_NAME)
    await db.leave_meta_queue(subject["id"], session_position, callback.from_user.id)

    text, kb = await _topics_screen(subject["id"], session_position)
    text = f"Вы вышли из очереди.\n\n{text}"
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
