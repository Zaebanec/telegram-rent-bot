from aiogram import F, Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, KeyboardButton, InputMediaPhoto
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.services.property_service import get_all_properties
from app.services.review_service import get_reviews_summary
from app.keyboards.inline_keyboards import (get_region_keyboard, get_district_keyboard, 
                                            get_property_card_keyboard, get_guests_keyboard)
from app.core.constants import DISTRICTS
from app.utils.states import SearchProperties

router = Router()

async def show_properties_by_filter(message: Message, state: FSMContext):
    """
    Финальная функция: собирает данные из состояния, делает запрос в БД и показывает результаты.
    """
    data = await state.get_data()
    properties = await get_all_properties(
        districts=data.get('districts'),
        max_price=data.get('max_price'),
        min_guests=data.get('min_guests')
    )
    
    await state.clear()

    if not properties:
        await message.answer("К сожалению, по вашему запросу ничего не найдено.")
        return

    await message.answer(f"Найдено {len(properties)} вариантов:")
    for prop in properties:
        avg_rating, reviews_count = await get_reviews_summary(prop.id)
        
        rating_info = ""
        if reviews_count > 0 and avg_rating is not None:
            rating_info = f"⭐️ **{avg_rating:.1f}/5.0** ({reviews_count} отзывов)\n"

        verified_icon = "✅" if prop.is_verified else ""
        rooms_str = f"{prop.rooms} комн." if prop.rooms > 0 else "Студия"
        
        caption = (
            f"{verified_icon} 🏠 **{prop.title}**\n"
            f"{rating_info}\n"
            f"📝 {prop.description}\n\n"
            f"📍 Район: {prop.district}\n"
            f"🗺️ Адрес: {prop.address}\n"
            f"🛏️ Комнаты: {rooms_str}\n"
            f"💰 Цена: {prop.price_per_night} руб/ночь\n"
            f"👥 Гостей: до {prop.max_guests}"
        )
        
        photo_files = [media.file_id for media in prop.media if media.media_type == 'photo']
        video_note_id = next((media.file_id for media in prop.media if media.media_type == 'video_note'), None)

        # Передаем актуальное количество фото и отзывов в клавиатуру
        keyboard = get_property_card_keyboard(prop.id, len(photo_files), bool(video_note_id), reviews_count)

        if video_note_id:
            await message.answer_video_note(video_note_id)
            await message.answer(caption, reply_markup=keyboard)
        elif photo_files:
            await message.answer_photo(
                photo=photo_files[0],
                caption=caption,
                reply_markup=keyboard
            )
        else:
            await message.answer(caption, reply_markup=keyboard)


def get_skip_keyboard():
    """Возвращает Reply-клавиатуру с кнопкой 'Пропустить'."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Пропустить"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# --- Логика Поиска (FSM) ---

@router.callback_query(F.data == "main_menu:search")
async def start_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Давайте подберем вам жилье. Выберите регион:", reply_markup=get_region_keyboard())
    await state.set_state(SearchProperties.region)
    await callback.answer()

@router.callback_query(SearchProperties.region, F.data.startswith("add_property_region:"))
async def search_select_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split(":")[1]
    await state.update_data(region=region)
    
    if region == "Куршская коса":
        await state.update_data(districts=[region]) # Сразу сохраняем как список
        await callback.message.edit_text("Район выбран. Укажите максимальную цену за ночь (или пропустите):")
        await callback.message.answer("Введите цену или нажмите 'Пропустить'", reply_markup=get_skip_keyboard())
        await state.set_state(SearchProperties.price)
    else:
        await callback.message.edit_text("Уточните локацию:", reply_markup=get_district_keyboard(region))
        await state.set_state(SearchProperties.district)
    await callback.answer()

@router.callback_query(SearchProperties.district, F.data == "back_to_regions")
async def search_back_to_regions(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите регион:", reply_markup=get_region_keyboard())
    await state.set_state(SearchProperties.region)
    await callback.answer()

# Новый обработчик для кнопки "Все варианты в регионе"
@router.callback_query(SearchProperties.district, F.data.startswith("search_all_in_region:"))
async def search_all_in_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split(":")[1]
    districts_in_region = DISTRICTS.get(region, [])
    
    await state.update_data(districts=districts_in_region)
    
    await callback.message.edit_text(f"Выбраны все варианты в '{region}'.")
    await callback.message.answer("Теперь укажите максимальную цену за ночь (или пропустите):", reply_markup=get_skip_keyboard())
    await state.set_state(SearchProperties.price)
    await callback.answer()

@router.callback_query(SearchProperties.district, F.data.startswith("add_prop_dist:"))
async def search_select_district(callback: CallbackQuery, state: FSMContext):
    _, region, district_index_str = callback.data.split(":")
    district_index = int(district_index_str)
    district_name = DISTRICTS[region][district_index]
    
    await state.update_data(districts=[district_name]) # Сохраняем как список
    
    await callback.message.edit_text("Район выбран. Укажите максимальную цену за ночь (или пропустите):")
    await callback.message.answer("Введите цену или нажмите 'Пропустить'", reply_markup=get_skip_keyboard())
    await state.set_state(SearchProperties.price)
    await callback.answer()

@router.message(SearchProperties.price)
async def search_by_price(message: Message, state: FSMContext):
    if message.text.lower() != 'пропустить':
        if not message.text.isdigit():
            await message.answer("Пожалуйста, введите цену цифрами.")
            return
        await state.update_data(max_price=int(message.text))
    
    await message.answer("Хорошо. На какое количество гостей ищете жилье?", reply_markup=ReplyKeyboardRemove())
    await message.answer("Выберите количество гостей:", reply_markup=get_guests_keyboard())
    await state.set_state(SearchProperties.guests)

@router.callback_query(SearchProperties.guests, F.data.startswith("add_property_guests:"))
async def search_by_guests(callback: CallbackQuery, state: FSMContext):
    guests = callback.data.split(":")[1]
    value_to_save = int(guests.replace('+', ''))
    await state.update_data(min_guests=value_to_save)
    
    await callback.message.edit_text(f"Выбрано гостей: {guests}. Идет поиск...")
    
    await show_properties_by_filter(callback.message, state)
    await callback.answer()

@router.message(StateFilter(SearchProperties), Command("cancel"))
@router.message(StateFilter(SearchProperties), F.text.casefold() == "отмена")
async def cancel_search_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Поиск отменен.", reply_markup=ReplyKeyboardRemove())

@router.message(StateFilter(SearchProperties))
async def incorrect_search_input(message: Message):
    await message.answer("Пожалуйста, следуйте инструкциям или нажмите на кнопки. Для отмены поиска введите /cancel")