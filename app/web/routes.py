import calendar
from datetime import date, datetime
from aiohttp import web
import aiohttp_cors

# Импортируем все необходимые сервисы
from app.services import availability_service, booking_service, pricing_service
from app.services.db import async_session_maker

async def get_calendar_data(request: web.Request) -> web.Response:
    """
    API эндпоинт для получения данных для календарей (клиентского и владльческого).
    Возвращает список дней для указанного месяца с их статусами и ценами.
    """
    try:
        # Извлекаем обязательные параметры из URL
        property_id = int(request.match_info['property_id'])
        # Извлекаем необязательные параметры (год и месяц), по умолчанию - текущие
        year = int(request.query.get('year', date.today().year))
        month = int(request.query.get('month', date.today().month))
    except (ValueError, KeyError):
        return web.json_response({'error': 'Invalid or missing parameters'}, status=400)

    async with async_session_maker() as session:
        # Получаем объект с его базовой ценой
        prop = await pricing_service.get_property_with_price_rules(session, property_id)
        if not prop:
            return web.json_response({'error': 'Property not found'}, status=404)
        base_price = prop.price_per_night

        # Получаем все даты, заблокированные владельцем вручную
        manual_blocks = await availability_service.get_manual_blocks(property_id)
        manual_block_map = {block.date: block.comment for block in manual_blocks}
        
        # Получаем все даты, занятые подтвержденными бронированиями
        booked_dates = await booking_service.get_booked_dates_for_property(property_id)
        
        days_data = []
        # Определяем количество дней в запрашиваемом месяце
        days_in_month = calendar.monthrange(year, month)[1]

        # Проходим по каждому дню месяца
        for day_num in range(1, days_in_month + 1):
            current_date = date(year, month, day_num)
            status = 'available'  # По умолчанию день свободен
            comment = None

            # Определяем статус дня
            if current_date < date.today():
                status = 'past'  # Прошедшая дата
            elif current_date in booked_dates:
                status = 'booked'  # Занято подтвержденной бронью
            elif current_date in manual_block_map:
                status = 'manual_block'  # Заблокировано владельцем
                comment = manual_block_map[current_date]
            
            price = None
            # Цену имеет смысл получать только для свободных дней
            if status == 'available':
                price = await pricing_service.get_price_for_date(session, property_id, current_date, base_price)
            
            days_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'status': status,
                'price': price,
                'comment': comment
            })
            
    return web.json_response(days_data)

# Функции toggle_availability и add_price_rule остаются без изменений,
# так как они относятся к Web App владельца и уже работают.

async def toggle_availability(request: web.Request) -> web.Response:
    """Блокирует или разблокирует дату (для владельца)."""
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
    """Добавляет новое ценовое правило (для владельца)."""
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

def setup_routes(app: web.Application):
    """Настраивает все веб-роуты с поддержкой CORS."""
    # Отдаем статические файлы (html, css, js)
    app.router.add_static('/static/', path='app/static', name='static')
    
    # Настраиваем CORS, чтобы разрешить запросы от Telegram Web App
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True, expose_headers="*",
            allow_headers="*", allow_methods="*",
        )
    })
    
    # Регистрируем наши API эндпоинты
    calendar_resource = cors.add(app.router.add_resource('/api/calendar_data/{property_id}'))
    cors.add(calendar_resource.add_route("GET", get_calendar_data))
    
    toggle_resource = cors.add(app.router.add_resource('/api/owner/toggle_availability'))
    cors.add(toggle_resource.add_route("POST", toggle_availability))
    
    pricing_resource = cors.add(app.router.add_resource('/api/owner/price_rule'))
    cors.add(pricing_resource.add_route("POST", add_price_rule))