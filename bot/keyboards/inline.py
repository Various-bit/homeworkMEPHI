from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def subjects_kb(subjects: list[dict], prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for subject in subjects:
        builder.button(text=subject["name"], callback_data=f"{prefix}:{subject['id']}")
    builder.adjust(1)
    return builder.as_markup()


def dates_kb(subject_id: int, dates: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for date in dates:
        builder.button(text=date, callback_data=f"date:{subject_id}:{date}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ К предметам", callback_data="back_subjects"))
    return builder.as_markup()


def homework_list_kb(subject_id: int, date: str, items: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=f"№{item['id']} · {item['created_at'][11:16]}", callback_data=f"hw:{item['id']}")
    builder.button(text="⬅️ К датам", callback_data=f"subj:{subject_id}")
    builder.adjust(1)
    return builder.as_markup()


def back_to_homework_kb(
    subject_id: int, date: str, homework_id: int | None = None, can_delete: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_delete and homework_id is not None:
        builder.row(InlineKeyboardButton(text="🗑 Удалить ДЗ", callback_data=f"delhw:{homework_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"date:{subject_id}:{date}"))
    return builder.as_markup()


def confirm_homework_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Сохранить", callback_data="confirm_hw")
    builder.button(text="❌ Отмена", callback_data="cancel_hw")
    builder.adjust(2)
    return builder.as_markup()


def confirm_delete_homework_kb(homework_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"delhw_yes:{homework_id}")
    builder.button(text="❌ Отмена", callback_data=f"delhw_no:{homework_id}")
    builder.adjust(2)
    return builder.as_markup()


def meta_sessions_overview_kb(totals: dict[int, int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for position, count in sorted(totals.items()):
        builder.button(text=f"Занятие {position} — {count} чел.", callback_data=f"msession:{position}")
    builder.adjust(1)
    return builder.as_markup()


def meta_topics_for_session_kb(session_position: int, topics: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for topic in topics:
        builder.button(
            text=f"Тема {topic['number']} — {topic['people_count']} чел.",
            callback_data=f"mtopic:{session_position}:{topic['id']}",
        )
    builder.button(text="⬅️ К занятиям", callback_data="mback")
    builder.adjust(1)
    return builder.as_markup()


def meta_cell_detail_kb(session_position: int, joined: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if joined:
        builder.button(text="🚪 Выйти из очереди", callback_data=f"mleave:{session_position}")
    builder.button(text="⬅️ К темам", callback_data=f"msession:{session_position}")
    builder.adjust(1)
    return builder.as_markup()


def admins_list_kb(admins: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for admin in admins:
        label = admin["full_name"] or admin["username"] or str(admin["user_id"])
        builder.button(text=f"🗑 {label}", callback_data=f"deladmin:{admin['user_id']}")
    builder.adjust(1)
    return builder.as_markup()
