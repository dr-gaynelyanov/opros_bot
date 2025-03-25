import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
from typing import Any, Awaitable, Callable, Dict, Union
from aiogram.types import Message, CallbackQuery
from database.database import get_db
from database.init_db import init_db
from middleware.database import DatabaseMiddleware

load_dotenv()
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=storage)

init_db()

from handlers.common import common_router
from handlers.admin import admin_router
from handlers.poll import poll_router

dp.update.middleware(DatabaseMiddleware())

dp.include_router(common_router)
dp.include_router(admin_router)
dp.include_router(poll_router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
