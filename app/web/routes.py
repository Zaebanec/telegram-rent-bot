import calendar
from datetime import date, datetime
from aiohttp import web
import aiohttp_cors

# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Убираем лишние импорты, которые создавали цикл ---
# from aiogram import Bot, Dispatcher -> НЕ НУЖНО
# from aiogram.types import Update -> НЕ НУЖНО
# from app.web.routes import setup_routes -> НЕ НУЖНО
from aiogram.types import Update # Этот импорт все же нужен для Update.model_validate

# Импортируем только то, что действительно используется в этом файле
from app.services import availability_service, booking_service, pricing_service
from app.services.db import async_session_maker

# --- ОБРАБОТЧИК ДЛЯ ВЕБХУКА ---
async def webhook_handler(request: web.Request) -> web.Response:
    """
    Принимает обновления от Telegram и передает их в диспетчер.
    """
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != request.app["webhook_secret"]:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    # Получаем нужные объекты из контекста приложения, а не импортируем их
    dp = request.app["dp"]
    bot = request.app["bot"]
    
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    
    return web.Response()

# --- ОБРАБОТЧИК ДЛЯ КЛИЕНТСКОГО WEB APP ---
async def client_webapp_handler(request: web.Request) -> web.Response:
    return web.FileResponse('app/static/index.html')

# --- API ДЛЯ КАЛЕНДАРЯ (без изменений) ---
async def get_calendar_data(request: web.Request) -> web.Response:
    # ... (код этой функции не меняется)
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

# --- API ДЛЯ WEB APP ВЛАДЕЛЬЦА (без изменений) ---
async def toggle_availability(request: web.Request) -> web.Response:
    # ... (код этой функции не меняется)
    try:
        data = await request.json()
        property_id = int(data['property_id'])
        target_date_str = data['date']
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        comment = data.get('comment')
    except Exception:
        return web.json_response({'error': 'Invalid request body'}, status=400)
    booked_dates = await booking_service.get_booked_dates_for_property(property_id)
    if target_date in booked_dates:
        return web.json_response({'error': 'Date is already booked by a client'}, status=409)
    await availability_service.toggle_manual_availability(property_id, target_date, comment)
    return web.json_response({'status': 'ok'})

async def add_price_rule(request: web.Request) -> web.Response:
    # ... (код этой функции не меняется)
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

# --- ФУНКЦИЯ НАСТРОЙКИ ВСЕХ РОУТОВ ---
def setup_routes(app: web.Application):
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
    
    toggle_resource = cors.add(app.router.add_resource('/api/owner/toggle_availability'))
    cors.add(toggle_resource.add_route("POST", toggle_availability))
    
    pricing_resource = cors.add(app.router.add_resource('/api/owner/price_rule'))
    cors.add(pricing_resource.add_route("POST", add_price_rule))