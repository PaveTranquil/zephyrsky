import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import dotenv_values, set_key
from pymorphy2 import MorphAnalyzer

from database import Database

get = lambda key: dotenv_values(".env").get(key)
set_ = lambda key, value: set_key(".env", key, value.encode("utf-8").decode("windows-1251"))


bot = Bot(get("BOT_TOKEN"), parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
morph = MorphAnalyzer()

db = Database(get("DATABASE_URL"))
scheduler = AsyncIOScheduler()
try:
    ADMINS = [int(admin) for admin in get("ADMINS").replace(", ", ",").split(",")]
except (AttributeError, ValueError):
    print("Добавьте в .env список админов через запятую")
    sys.exit(1)
