from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import Config
from bot.database import requests as db
from bot.filters.roles import IsSuperAdmin
from bot.keyboards.reply import main_menu, cancel_kb
from bot.keyboards.inline import admins_list_kb
from bot.states.states import ManageAdmins

router = Router()
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


@router.message(F.text == "👤 Управление админами")
async def manage_admins(message: Message, state: FSMContext) -> None:
    admins = await db.list_admins()

    if admins:
        text = "Текущие админы (могут добавлять ДЗ):"
    else:
        text = "Пока нет ни одного добавленного админа."

    await message.answer(text, reply_markup=admins_list_kb(admins) if admins else None)
    await state.set_state(ManageAdmins.waiting_for_user)
    await message.answer(
        "Чтобы добавить нового админа — перешлите сюда любое его сообщение "
        "или пришлите его числовой Telegram ID.",
        reply_markup=cancel_kb(),
    )


@router.message(ManageAdmins.waiting_for_user, F.forward_from)
async def add_admin_from_forward(message: Message, state: FSMContext, config: Config) -> None:
    user = message.forward_from
    await db.add_admin(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        added_by=message.from_user.id,
    )
    await state.clear()
    await message.answer(
        f"✅ {user.full_name} добавлен(а) в админы.",
        reply_markup=main_menu(is_admin=True, is_super_admin=True),
    )


@router.message(ManageAdmins.waiting_for_user, F.text)
async def add_admin_from_id(message: Message, state: FSMContext, config: Config) -> None:
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(
            "Не похоже на Telegram ID. Перешлите сообщение пользователя "
            "или пришлите его числовой ID, либо нажмите «❌ Отмена»."
        )
        return

    user_id = int(text)
    await db.add_admin(user_id=user_id, username=None, full_name=f"ID {user_id}", added_by=message.from_user.id)
    await state.clear()
    await message.answer(
        f"✅ Пользователь с ID {user_id} добавлен(а) в админы.",
        reply_markup=main_menu(is_admin=True, is_super_admin=True),
    )


@router.callback_query(F.data.startswith("deladmin:"))
async def delete_admin(callback: CallbackQuery) -> None:
    user_id = int(callback.data.removeprefix("deladmin:"))
    await db.remove_admin(user_id)

    admins = await db.list_admins()
    if admins:
        await callback.message.edit_text("Текущие админы (могут добавлять ДЗ):", reply_markup=admins_list_kb(admins))
    else:
        await callback.message.edit_text("Пока нет ни одного добавленного админа.")

    await callback.answer("Админ удалён")
