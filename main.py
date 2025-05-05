import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from handlers import router  # теперь импорт будет работать
from database.sqlite import Database
from middlewares.database import DatabaseMiddleware

logger = logging.getLogger(__name__)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    config = load_config()
    storage = MemoryStorage()
    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher(storage=storage)
    
    database = Database(config.db.database)
    dp.message.middleware(DatabaseMiddleware(database))
    dp.callback_query.middleware(DatabaseMiddleware(database))
    
    dp.include_router(router)
    
    logger.info("Starting bot")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
