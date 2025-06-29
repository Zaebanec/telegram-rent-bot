from datetime import datetime, timedelta
from typing import List
from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram_calendar import SimpleCalendar

from app.core.constants import DISTRICTS, PROPERTY_TYPES, ROOM_OPTIONS, GUEST_OPTIONS
# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Импортируем наши настройки ---
from app.core.settings import settings

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Найти жилье", callback_data="main_menu:search")
    builder.button(text="🏠 Добавить объект", callback_data="main_menu:add_property")
    builder.button(text="ℹ️ О сервисе", callback_data="main_menu:about")
    builder.adjust(1)
    return builder.as_markup()

def get_property_card_keyboard(property_id: int, photos_count: int = 0, has_video: bool = False, reviews_count: int = 0):
    builder = InlineKeyboardBuilder()
    total_media_count = photos_count + (1 if has_video else 0)

    if has_video:
        builder.button(text=f"▶️ Видео и фото ({total_media_count})", callback_data=f"view_media:{property_id}")
    elif photos_count > 1:
        builder.button(text=f"📸 Все фото ({photos_count})", callback_data=f"view_photos:{property_id}")

    if reviews_count > 0:
        builder.button(text=f"💬 Читать отзывы ({reviews_count})", callback_data=f"view_reviews:{property_id}")
    
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Формируем правильный URL из настроек ---
    web_app_url = f"{settings.WEB_APP_BASE_URL}/webapp/client?property_id={property_id}"

    builder.button(text="📅 Забронировать", web_app=WebAppInfo(url=web_app_url))
    
    builder.adjust(1)
    return builder.as_markup()

def get_rating_keyboard(booking_id: int):
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text=f"⭐️ {i}", callback_data=f"review:{booking_id}:rating:{i}")
    builder.adjust(5)
    return builder.as_markup()

async def get_calendar():
    calendar = SimpleCalendar()
    calendar.set_dates_range(datetime.now(), datetime.now() + timedelta(days=365))
    return await calendar.start_calendar()

def get_region_keyboard():
    builder = InlineKeyboardBuilder()
    for region in DISTRICTS.keys():
        builder.button(text=region, callback_data=f"add_property_region:{region}")
    builder.adjust(2)
    return builder.as_markup()

def get_district_keyboard(region: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"➡️ Все варианты в '{region}'", callback_data=f"search_all_in_region:{region}")
    for index, district_name in enumerate(DISTRICTS[region]):
        builder.button(text=district_name, callback_data=f"add_prop_dist:{region}:{index}")
    builder.button(text="🔙 Назад", callback_data="back_to_regions")
    builder.adjust(1)
    return builder.as_markup()

def get_rooms_keyboard():
    builder = InlineKeyboardBuilder()
    for option in ROOM_OPTIONS:
        builder.button(text=option, callback_data=f"add_property_rooms:{option}")
    builder.adjust(3)
    return builder.as_markup()

def get_guests_keyboard():
    builder = InlineKeyboardBuilder()
    for option in GUEST_OPTIONS:
        builder.button(text=option, callback_data=f"add_property_guests:{option}")
    builder.adjust(4)
    return builder.as_markup()

def get_property_types_keyboard():
    builder = InlineKeyboardBuilder()
    for prop_type in PROPERTY_TYPES:
        builder.button(text=prop_type, callback_data=f"add_property_type:{prop_type}")
    builder.adjust(2)
    return builder.as_markup()

def get_property_management_keyboard(property_id: int, is_active: bool):
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.button(text="🔴 Скрыть", callback_data=f"manage:toggle:{property_id}")
    else:
        builder.button(text="🟢 Активировать", callback_data=f"manage:toggle:{property_id}")
    builder.button(text="✏️ Редактировать", callback_data=f"manage:edit:{property_id}")
    builder.button(text="🗑️ Удалить", callback_data=f"manage:delete:{property_id}")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_delete_confirmation_keyboard(property_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"manage:delete_confirm:{property_id}")
    builder.button(text="❌ Отмена", callback_data=f"manage:delete_cancel")
    return builder.as_markup()

def get_edit_property_keyboard(property_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data=f"edit_prop:title:{property_id}")
    builder.button(text="Описание", callback_data=f"edit_prop:description:{property_id}")
    builder.button(text="Адрес", callback_data=f"edit_prop:address:{property_id}")
    builder.button(text="Кол-во комнат", callback_data=f"edit_prop:rooms:{property_id}")
    builder.button(text="Цену", callback_data=f"edit_prop:price:{property_id}")
    builder.button(text="Кол-во гостей", callback_data=f"edit_prop:guests:{property_id}")
    builder.button(text="Тип объекта", callback_data=f"edit_prop:type:{property_id}")
    builder.button(text="📸 Управлять фото/видео", callback_data=f"edit_prop:media:{property_id}")
    
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: URL для Web App владельца ---
    owner_web_app_url = f"{settings.WEB_APP_BASE_URL}/static/owner.html?property_id={property_id}"
    builder.button(text="🗓️ Управлять доступностью", web_app=WebAppInfo(url=owner_web_app_url))
    
    builder.button(text="🔙 Назад к списку", callback_data="back_to_my_properties")
    builder.adjust(2, 2, 2, 1, 1, 1) # Немного поправил верстку
    return builder.as_markup()

def get_delete_one_media_keyboard(media_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑️ Удалить это медиа", callback_data=f"edit_media:delete:{media_id}")
    return builder.as_markup()

def get_media_management_keyboard(property_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить еще фото/видео", callback_data=f"edit_media:add:{property_id}")
    builder.button(text="✅ Готово", callback_data=f"edit_media:done:{property_id}")
    builder.adjust(1)
    return builder.as_markup()

def get_finish_upload_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Завершить загрузку")], [KeyboardButton(text="Отмена")]], resize_keyboard=True)

def get_skip_video_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Пропустить этот шаг")], [KeyboardButton(text="Отмена")]], resize_keyboard=True, one_time_keyboard=True)

def get_booking_management_keyboard(booking_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"booking:confirm:{booking_id}")
    builder.button(text="❌ Отклонить", callback_data=f"booking:reject:{booking_id}")
    builder.adjust(2)
    return builder.as_markup()