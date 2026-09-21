import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.database.db import init_db, set_db_path
from bot.handlers import common, student, admin, superadmin, queue


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    set_db_path(config.db_path)
    await init_db()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(superadmin.router)
    dp.include_router(admin.router)
    dp.include_router(queue.router)
    dp.include_router(student.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, config=config)


if __name__ == "__main__":
    asyncio.run(main())
