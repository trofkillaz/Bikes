import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import menu, create_rent, open_requests, close_rent

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(menu.router)
    dp.include_router(create_rent.router)
    dp.include_router(open_requests.router)
    dp.include_router(close_rent.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())