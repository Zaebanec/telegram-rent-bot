import asyncio
import logging
import sys
from aiohttp import web
import aiohttp_cors
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- ИМПОРТЫ ТЕПЕРЬ СНОВА НАЧИНАЮТСЯ С `src` ---
from src.core.settings import settings
from src.core.commands import set_commands
from src.core.scheduler import scheduler
from src.handlers import main_router
from src.web.routes import (webhook_handler, client_webapp_handler, 
                            get_calendar_data, create_booking_handler)
from src.middlewares.error_catcher import ErrorCatcherMiddleware

async def on_startup(app: web.Application):
    bot: Bot = app["bot"]
    base_url = app["base_url"]
    webhook_secret = app["webhook_secret"]
    await set_commands(bot)
    await bot.set_webhook(
        f"{base_url}/webhook",
        secret_token=webhook_secret,
        allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"]
    )
    logging.info("Webhook has been set successfully.")

async def on_shutdown(app: web.Application):
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
    dp.update.outer_middleware(ErrorCatcherMiddleware())
    dp.include_router(main_router)
    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp
    app["base_url"] = settings.WEB_APP_BASE_URL
    app["webhook_secret"] = settings.WEBHOOK_SECRET.get_secret_value()
    # --- ПУТЬ К STATIC СНОВА СТАНОВИТСЯ ПРОСТЫМ ---
    app.router.add_static('/static/', path='src/static', name='static')
    app.router.add_get("/webapp/client", client_webapp_handler)
    app.router.add_post("/webhook", webhook_handler)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True, expose_headers="*",
            allow_headers="*", allow_methods="*",
        )
    })
    calendar_resource = cors.add(app.router.add_resource('/api/calendar_data/{property_id}'))
    cors.add(calendar_resource.add_route("GET", get_calendar_data))
    booking_resource = cors.add(app.router.add_resource('/api/bookings/create'))
    cors.add(booking_resource.add_route("POST", create_booking_handler))
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    scheduler.start()
    try:
        web.run_app(app, host="0.0.0.0", port=8080)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")