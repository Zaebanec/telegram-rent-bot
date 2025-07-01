import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiohttp import web
import aiohttp_cors

from src.core.settings import settings
from src.core.commands import set_commands
from src.core.scheduler import scheduler
from src.handlers import main_router
# Импортируем все необходимые обработчики из routes.py
from src.web.routes import (
    webhook_handler, 
    client_webapp_handler, 
    get_calendar_data,
    toggle_availability,
    add_price_rule
)

# --- ТЕСТОВЫЙ ОБРАБОТЧИК (можно будет удалить после завершения отладки) ---
async def temporary_webapp_catcher(message: Message):
    logging.critical("="*50)
    logging.critical("!!! WEB APP CATCHER WORKED !!!")
    logging.critical(f"DATA RECEIVED: {message.web_app_data.data}")
    logging.critical("="*50)
    await message.answer("✅ **Бэкенд поймал данные!**")

# --- НОВЫЙ ОБРАБОТЧИК ДЛЯ WEB APP ВЛАДЕЛЬЦА ---
async def owner_webapp_handler(request: web.Request) -> web.Response:
    """
    Этот обработчик отдает HTML-файл для Web App владельца.
    """
    return web.FileResponse('src/static/owner.html')


# --- ФУНКЦИИ ЖИЗНЕННОГО ЦИКЛА ПРИЛОЖЕНИЯ ---
async def on_startup(app: web.Application):
    """Выполняется при старте приложения."""
    bot: Bot = app["bot"]
    base_url = app["base_url"]
    webhook_secret = app["webhook_secret"]
    
    await set_commands(bot)
    await bot.set_webhook(
        f"{base_url}/webhook",
        secret_token=webhook_secret,
        allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"]
    )
    logging.info("Webhook has been set.")

async def on_shutdown(app: web.Application):
    """Выполняется при остановке приложения."""
    bot: Bot = app["bot"]
    await bot.delete_webhook()
    logging.info("Webhook has been deleted.")


# --- ГЛАВНАЯ ТОЧКА ВХОДА ---
if __name__ == "__main__":
    # Настраиваем логирование
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Инициализируем бота и диспетчер
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрируем роутеры aiogram
    dp.message.register(temporary_webapp_catcher, F.web_app_data)
    dp.include_router(main_router)

    # Создаем веб-приложение aiohttp
    app = web.Application()
    
    # Сохраняем в контекст приложения нужные нам объекты для доступа из обработчиков
    app["bot"] = bot
    app["dp"] = dp
    app["base_url"] = settings.WEB_APP_BASE_URL
    app["webhook_secret"] = settings.WEBHOOK_SECRET.get_secret_value()

    # --- РЕГИСТРАЦИЯ РОУТОВ AIOHTTP ---
    app.router.add_static('/static/', path='src/static', name='static')
    app.router.add_get("/webapp/client", client_webapp_handler)
    app.router.add_get("/webapp/owner", owner_webapp_handler) # <-- Роут для Web App владельца
    app.router.add_post("/webhook", webhook_handler)
    
    # Настраиваем CORS для всех API-эндпоинтов
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True, expose_headers="*",
            allow_headers="*", allow_methods="*",
        )
    })
    
    # Регистрируем API-эндпоинты и оборачиваем их в CORS
    calendar_resource = cors.add(app.router.add_resource('/api/calendar_data/{property_id}'))
    cors.add(calendar_resource.add_route("GET", get_calendar_data))
    
    toggle_resource = cors.add(app.router.add_resource('/api/owner/toggle_availability'))
    cors.add(toggle_resource.add_route("POST", toggle_availability))
    
    pricing_resource = cors.add(app.router.add_resource('/api/owner/price_rule'))
    cors.add(pricing_resource.add_route("POST", add_price_rule))
    # --- КОНЕЦ БЛОКА РЕГИСТРАЦИИ РОУТОВ ---

    # Регистрируем функции, которые выполнятся при старте и остановке приложения
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Запускаем планировщик фоновых задач
    scheduler.start()

    # Запускаем веб-приложение
    try:
        web.run_app(app, host="0.0.0.0", port=8080)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")