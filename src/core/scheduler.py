from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.core.settings import settings
# --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Указываем новый, правильный путь к файлу ---
from src.keyboards.inline_keyboards import get_rating_keyboard

jobstores = {
    'default': SQLAlchemyJobStore(url=settings.DATABASE_URL_psycopg)
}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Europe/Kaliningrad")


async def request_review(bot_token: str, chat_id: int, booking_id: int, property_title: str):
    """
    Запрашивает у пользователя отзыв о проживании.
    """
    temp_bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await temp_bot.send_message(
            chat_id=chat_id,
            text=(
                f"Надеемся, вам понравилось проживание в «{property_title}»!\n\n"
                f"Пожалуйста, оцените ваш опыт по пятизвездочной шкале. Это поможет другим путешественникам сделать правильный выбор."
            ),
            reply_markup=get_rating_keyboard(booking_id)
        )
    finally:
        await temp_bot.session.close()