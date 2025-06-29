import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from app.core.settings import settings
from app.core.commands import set_commands
from app.core.scheduler import scheduler
from app.handlers import main_router
from app.web.routes import setup_routes  # <-- Наш новый импорт

async def start_bot(dp: Dispatcher, bot: Bot):
    """Запускает процесс поллинга бота."""
    await set_commands(bot)
    dp.include_router(main_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def start_web_server():
    """Запускает веб-сервер для API."""
    app = web.Application()
    setup_routes(app) # Настраиваем роуты для API
    runner = web.AppRunner(app)
    await runner.setup()
    # Запускаем на порту 8080, как требует большинство хостингов
    site = web.TCPSite(runner, '0.0.0.0', 8080) 
    await site.start()
    logging.info("Web server started on http://0.0.0.0:8080")
    # Бесконечно ждем, пока сервер работает
    while True:
        await asyncio.sleep(3600)

async def main():
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Запускаем планировщик
    scheduler.start()
    
    # Запускаем бота и веб-сервер параллельно
    await asyncio.gather(
        start_bot(dp, bot),
        start_web_server()
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("App stopped by admin.")

