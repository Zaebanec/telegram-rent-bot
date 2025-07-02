import asyncio
import logging
import sys
from pathlib import Path # <--- ИМПОРТИРУЕМ PATHLIB

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
from src.web.routes import (
    webhook_handler, 
    client_webapp_handler, 
    owner_webapp_handler,
    get_calendar_data,
    set_availability,
    add_price_rule
)

# ---> НАЧАЛО КЛЮЧЕВОГО ИЗМЕНЕНИЯ <---
# Определяем абсолютный путь к корню проекта.
# В Docker это будет /src
ROOT_DIR = Path(__file__).parent
# ---> КОНЕЦ КЛЮЧЕВОГО ИЗМЕНЕНИЯ <---


async def on_startup(app: web.Application):
    # ... (код on_startup без изменений) ...
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
    # ... (код on_shutdown без изменений) ...
    bot: Bot = app["bot"]
    await bot.delete_webhook()
    logging.info("Webhook has been deleted.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(main_router)

    app = web.Application()
    
    # ---> НАЧАЛО КЛЮЧЕВОГО ИЗМЕНЕНИЯ <---
    # Сохраняем абсолютный путь в приложении
    app["root_dir"] = ROOT_DIR 
    # ---> КОНЕЦ КЛЮЧЕВОГО ИЗМЕНЕНИЯ <---

    app["bot"] = bot
    app["dp"] = dp
    app["base_url"] = settings.WEB_APP_BASE_URL
    app["webhook_secret"] = settings.WEBHOOK_SECRET.get_secret_value()
    
    # ---> НАЧАЛО КЛЮЧЕВОГО ИЗМЕНЕНИЯ <---
    # Теперь мы строим путь к статике от абсолютного корня
    app.router.add_static('/static/', path=(ROOT_DIR / 'src' / 'static'), name='static')
    # ---> КОНЕЦ КЛЮЧЕВОГО ИЗМЕНЕНИЯ <---
    
    app.router.add_get("/webapp/client", client_webapp_handler)
    app.router.add_get("/webapp/owner", owner_webapp_handler)
    app.router.add_post("/webhook", webhook_handler)
    
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True, expose_headers="*",
            allow_headers="*", allow_methods="*",
        )
    })
    
    calendar_resource = cors.add(app.router.add_resource('/api/calendar_data/{property_id}'))
    cors.add(calendar_resource.add_route("GET", get_calendar_data))
    
    set_availability_resource = cors.add(app.router.add_resource('/api/owner/set_availability'))
    cors.add(set_availability_resource.add_route("POST", set_availability))
    
    pricing_resource = cors.add(app.router.add_resource('/api/owner/price_rule'))
    cors.add(pricing_resource.add_route("POST", add_price_rule))

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    scheduler.start()

    try:
        web.run_app(app, host="0.0.0.0", port=8080)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")