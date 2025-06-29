import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiohttp import web

from app.core.settings import settings
from app.core.commands import set_commands
from app.core.scheduler import scheduler
from app.handlers import main_router
from app.web.routes import setup_routes

# --- НАШ ТЕСТОВЫЙ ОБРАБОТЧИК ---
async def temporary_webapp_catcher(message: Message):
    logging.critical("="*50)
    logging.critical("!!! WEB APP CATCHER WORKED !!!")
    logging.critical(f"DATA RECEIVED: {message.web_app_data.data}")
    logging.critical("="*50)
    await message.answer("✅ **Бэкенд поймал данные!**")

# --- ФУНКЦИИ ЗАПУСКА/ОСТАНОВКИ ---
async def on_startup(app: web.Application):
    """Выполняется при старте приложения."""
    bot: Bot = app["bot"]
    base_url = app["base_url"]
    webhook_secret = app["webhook_secret"]
    
    await set_commands(bot)
    await bot.set_webhook(
        f"{base_url}/webhook",
        secret_token=webhook_secret
    )
    logging.info("Webhook has been set.")

async def on_shutdown(app: web.Application):
    """Выполняется при остановке приложения."""
    bot: Bot = app["bot"]
    await bot.delete_webhook()
    logging.info("Webhook has been deleted.")

# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Упрощаем точку входа ---
if __name__ == "__main__":
    # Настраиваем логирование
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Инициализируем бота и диспетчер
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрируем тестовый обработчик первым
    dp.message.register(temporary_webapp_catcher, F.web_app_data)
    # Регистрируем все остальные роутеры
    dp.include_router(main_router)

    # Создаем приложение aiohttp
    app = web.Application()
    
    # Сохраняем в контекст приложения нужные нам объекты
    app["bot"] = bot
    app["dp"] = dp
    app["base_url"] = settings.WEB_APP_BASE_URL
    app["webhook_secret"] = settings.WEBHOOK_SECRET.get_secret_value()

    # Регистрируем обработчики старта и остановки
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Настраиваем роуты
    setup_routes(app)

    # Запускаем планировщик
    scheduler.start()

    # Запускаем веб-приложение. Это блокирующая операция, она сама управляет циклом.
    try:
        web.run_app(app, host="0.0.0.0", port=8080)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")