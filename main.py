import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiohttp import web
import aiohttp_cors

from app.core.settings import settings
from app.core.commands import set_commands
from app.core.scheduler import scheduler
from app.handlers import main_router
from app.web.routes import webhook_handler, client_webapp_handler, get_calendar_data

async def temporary_webapp_catcher(message: Message):
    logging.critical("="*50)
    logging.critical("!!! WEB APP CATCHER WORKED !!!")
    logging.critical(f"DATA RECEIVED: {message.web_app_data.data}")
    logging.critical("="*50)
    await message.answer("✅ **Бэкенд поймал данные!**")

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
    logging.info("Webhook has been set.")

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
    
    dp.message.register(temporary_webapp_catcher, F.web_app_data)
    dp.include_router(main_router)

    app = web.Application()
    
    app["bot"] = bot
    app["dp"] = dp
    app["base_url"] = settings.WEB_APP_BASE_URL
    app["webhook_secret"] = settings.WEBHOOK_SECRET.get_secret_value()

    app.router.add_static('/static/', path='app/static', name='static')
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

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    scheduler.start()

    try:
        web.run_app(app, host="0.0.0.0", port=8080)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")