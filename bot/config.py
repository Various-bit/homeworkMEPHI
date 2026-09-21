import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    super_admin_ids: set[int]
    db_path: str


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    raw_ids = os.getenv("SUPER_ADMIN_IDS", "")
    super_admin_ids = {int(x) for x in raw_ids.replace(" ", "").split(",") if x}

    db_path = os.getenv("DB_PATH", "bot/database/homework.db")

    return Config(bot_token=token, super_admin_ids=super_admin_ids, db_path=db_path)
