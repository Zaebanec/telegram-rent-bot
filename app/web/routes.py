import logging
from datetime import date, datetime
import calendar
from aiohttp import web
import aiohttp_cors

from aiogram import Bot
# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Убираем импорт User отсюда ---
from aiogram.types import Update
# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Импортируем Pydantic для создания своей модели ---
from pydantic import BaseModel

from app.services import (availability_service, booking_service, pricing_service, 
                          get_property_with_media_and_owner, user_service)
from app.services.db import async_session_maker
from app.keyboards.inline_keyboards import get_booking_management_keyboard

# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Создаем нашу собственную модель для данных из Web App ---
class WebAppUser(BaseModel):
    """
    Модель для валидации данных пользователя, приходящих из Telegram Web App.
    Содержит только те поля, которые нам действительно нужны и которые там есть.
    """
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None


# --- ОБРАБОТЧИК ДЛЯ СОЗДАНИЯ БРОНИ ---
async def create_booking_handler(request: web.Request) -> web.Response:
    """
    API-эндпоинт для создания новой заявки на бронирование из Web App.
    """
    try:
        bot: Bot = request.app["bot"]
        data = await request.json()
        
        property_id = int(data['property_id'])
        checkin_date = datetime.fromisoformat(data['checkin_date'])
        checkout_date = datetime.fromisoformat(data['checkout_date'])
        total_price = data['total_price']
        
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Валидируем данные по нашей новой, легкой модели ---
        user_data = WebAppUser.model_validate(data['user'])

        # Гарантируем, что пользователь существует в БД
        await user_service.add_user(
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name
        )

        prop, _, _ = await get_property_with_media_and_owner(property_id)
        if not prop:
            return web.json_response({"error": "Property not found"}, status=404)

        if prop.owner.telegram_id == user_data.id:
            return web.json_response({"error": "You can't book your own property"}, status=400)

        new_booking = await booking_service.create_booking(
            user_id=user_data.id,
            property_id=property_id,
            start_date=checkin_date,
            end_date=checkout_date
        )

        user_info = f"@{user_data.username}" if user_data.username else user_data.first_name
        num_nights = (checkout_date - checkin_date).days

        await bot.send_message(
            chat_id=prop.owner.telegram_id,
            text=(
                f"🔔 Новая заявка на бронирование!\n\n"
                f"<b>Объект:</b> «{prop.title}»\n"
                f"<b>Даты:</b> с {checkin_date.strftime('%d.%m.%Y')} по {checkout_date.strftime('%d.%m.%Y')} ({num_nights} ночей)\n"
                f"<b>Сумма:</b> {total_price} руб.\n"
                f"<b>Гость:</b> {user_info} (ID: `{user_data.id}`)"
            ),
            reply_markup=get_booking_management_keyboard(new_booking.id)
        )
        
        return web.json_response({"status": "ok", "booking_id": new_booking.id})

    except Exception as e:
        logging.exception(f"Критическая ошибка при создании бронирования через API: {e}")
        return web.json_response({"error": "Internal server error"}, status=500)

# --- Остальные обработчики без изменений ---
# ... (код webhook_handler, client_webapp_handler, get_calendar_data)
async def webhook_handler(request: web.Request) -> web.Response:
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != request.app["webhook_secret"]:
        return web.json_response({"error": "Unauthorized"}, status=401)
    dp = request.app["dp"]
    bot = request.app["bot"]
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return web.Response()

async def client_webapp_handler(request: web.Request) -> web.Response:
    return web.FileResponse('app/static/index.html')

async def get_calendar_data(request: web.Request) -> web.Response:
    try:
        property_id = int(request.match_info['property_id'])
        year = int(request.query.get('year', date.today().year))
        month = int(request.query.get('month', date.today().month))
    except (ValueError, KeyError):
        return web.json_response({'error': 'Invalid or missing parameters'}, status=400)
    async with async_session_maker() as session:
        prop = await pricing_service.get_property_with_price_rules(session, property_id)
        if not prop:
            return web.json_response({'error': 'Property not found'}, status=404)
        base_price = prop.price_per_night
        manual_blocks = await availability_service.get_manual_blocks(property_id)
        manual_block_map = {block.date: block.comment for block in manual_blocks}
        booked_dates = await booking_service.get_booked_dates_for_property(property_id)
        days_data = []
        days_in_month = calendar.monthrange(year, month)[1]
        for day_num in range(1, days_in_month + 1):
            current_date = date(year, month, day_num)
            status = 'available'
            comment = None
            if current_date < date.today():
                status = 'past'
            elif current_date in booked_dates:
                status = 'booked'
            elif current_date in manual_block_map:
                status = 'manual_block'
                comment = manual_block_map[current_date]
            price = None
            if status == 'available':
                price = await pricing_service.get_price_for_date(session, property_id, current_date, base_price)
            days_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'status': status,
                'price': price,
                'comment': comment
            })
    return web.json_response(days_data)