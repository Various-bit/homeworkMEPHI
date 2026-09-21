from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import Config
from bot.database import requests as db
from bot.keyboards.reply import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, config: Config) -> None:
    is_super = message.from_user.id in config.super_admin_ids
    is_admin = is_super or await db.is_admin(message.from_user.id)

    await message.answer(
        "Привет! Это бот для домашних заданий группы.\n\n"
        "📚 «Посмотреть ДЗ» — список заданий по датам добавления.",
        reply_markup=main_menu(is_admin=is_admin, is_super_admin=is_super),
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cancel_any_state(message: Message, state: FSMContext, config: Config) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()

    is_super = message.from_user.id in config.super_admin_ids
    is_admin = is_super or await db.is_admin(message.from_user.id)
    await message.answer("Действие отменено.", reply_markup=main_menu(is_admin, is_super))
