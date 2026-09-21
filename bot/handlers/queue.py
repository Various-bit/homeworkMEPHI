from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.constants import META_SUBJECT_NAME
from bot.database import requests as db
from bot.keyboards.inline import meta_topic_detail_kb, meta_topics_kb

router = Router()


async def _topics_screen(subject_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    topics = await db.list_meta_topics_with_counts(subject_id)
    if not topics:
        return "Пока нет активных тем для записи.", None

    return f"Очередь на «{META_SUBJECT_NAME}»\nВыберите тему:", meta_topics_kb(topics)


@router.message(F.text == "📋 Очередь на метаязыки")
async def show_queue_menu(message: Message) -> None:
    subject = await db.get_subject_by_name(META_SUBJECT_NAME)
    if subject is None:
        await message.answer("Предмет не найден.")
        return

    text, kb = await _topics_screen(subject["id"])

    entry = await db.get_user_meta_queue_entry(subject["id"], message.from_user.id)
    if entry:
        position = await db.get_queue_position(entry["topic_id"], message.from_user.id)
        text = f"Вы в очереди на Тему {entry['number']} — вы {position}-й.\n\n{text}"

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "mback")
async def back_to_topics(callback: CallbackQuery) -> None:
    subject = await db.get_subject_by_name(META_SUBJECT_NAME)
    text, kb = await _topics_screen(subject["id"])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("mtopic:"))
async def open_topic(callback: CallbackQuery) -> None:
    topic_id = int(callback.data.removeprefix("mtopic:"))
    topic = await db.get_meta_topic(topic_id)
    if topic is None:
        await callback.answer("Эта тема больше не существует, список обновился.", show_alert=True)
        await back_to_topics(callback)
        return

    user_id = callback.from_user.id
    entry = await db.get_user_meta_queue_entry(topic["subject_id"], user_id)

    if entry and entry["topic_id"] != topic_id:
        await callback.answer(
            f"Вы уже в очереди на Тему {entry['number']}. Сначала выйдите из неё.",
            show_alert=True,
        )
        return

    if not entry:
        await db.join_meta_queue(topic_id, user_id, callback.from_user.full_name)

    position = await db.get_queue_position(topic_id, user_id)
    text = f"Тема {topic['number']}\nВы в очереди, ваша позиция: {position}."
    await callback.message.edit_text(text, reply_markup=meta_topic_detail_kb(topic_id, joined=True))
    await callback.answer()


@router.callback_query(F.data.startswith("mleave:"))
async def leave_topic(callback: CallbackQuery) -> None:
    topic_id = int(callback.data.removeprefix("mleave:"))
    topic = await db.get_meta_topic(topic_id)
    if topic is None:
        await callback.answer("Тема не найдена.", show_alert=True)
        return

    await db.leave_meta_queue(topic["subject_id"], callback.from_user.id)

    text, kb = await _topics_screen(topic["subject_id"])
    text = f"Вы вышли из очереди на Тему {topic['number']}.\n\n{text}"
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
