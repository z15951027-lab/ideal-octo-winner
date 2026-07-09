import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, SCHEDULER_INTERVAL_MIN
import db
from scheduler import setup_scheduler

from handlers import start, balance, channels, tasks, profile

logging.basicConfig(level=logging.INFO)


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise RuntimeError(
            "Не задан BOT_TOKEN. Создай файл .env на основе .env.example и укажи токен бота."
        )

    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(balance.router)
    dp.include_router(profile.router)
    dp.include_router(channels.router)
    dp.include_router(tasks.router)

    scheduler = setup_scheduler(bot, SCHEDULER_INTERVAL_MIN)
    scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
