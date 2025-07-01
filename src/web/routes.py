import calendar
from datetime import date, datetime
from aiohttp import web
from aiogram.types import Update

from src.services import availability_service, booking_service, pricing_service
from src.services.db import async_session_maker

# --- ОБРАБОТЧИКИ ---

async def webhook_handler(request: web.Request) -> web.Response:
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != request.app["webhook_secret"]:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    dp = request.app["dp"]
    bot = request.app["bot"]
    
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    
    return web.Response()

async def client_webapp_handler(request: web.Request) -> web.Response:
    return web.FileResponse('src/static/index.html')

# --- ИЗМЕНЕНИЕ: Возвращаем обработчик для Web App владельца ---
async def owner_webapp_handler(request: web.Request) -> web.Response:
    return web.FileResponse('src/static/owner.html')

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

# --- ИЗМЕНЕНИЕ: Возвращаем обработчик для установки доступности ---
async def set_availability(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        property_id = int(data['property_id'])
        dates_str = data['dates']
        dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in dates_str]
        is_available = bool(data['is_available'])
        comment = data.get('comment')
    except Exception:
        return web.json_response({'error': 'Invalid request body'}, status=400)
    
    await availability_service.set_availability_for_period(property_id, dates, is_available, comment)
    return web.json_response({'status': 'ok'})

async def add_price_rule(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        property_id = int(data['property_id'])
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        price = int(data['price'])
    except Exception:
        return web.json_response({'error': 'Invalid request body'}, status=400)
    await pricing_service.add_price_rule(property_id, start_date, end_date, price)
    return web.json_response({'status': 'ok'})