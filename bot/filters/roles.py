from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery

from bot.config import Config
from bot.database import requests as db


class IsSuperAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        return event.from_user.id in config.super_admin_ids


class IsAdmin(Filter):
    """Супер-админ ИЛИ человек, добавленный супер-админом как ответственный за ДЗ."""

    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        user_id = event.from_user.id
        if user_id in config.super_admin_ids:
            return True
        return await db.is_admin(user_id)
