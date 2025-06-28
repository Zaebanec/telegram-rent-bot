import logging
from datetime import datetime, date
from aiogram import F, Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (Message, CallbackQuery, ReplyKeyboardRemove,
                           InputMediaPhoto, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from app.services import availability_service, booking_service
from app.utils.states import EditProperty
from app.services.property_service import get_property_with_media_and_owner, update_property_field
from app.services.media_service import (delete_one_media_item, add_photos_to_property,
                                        add_video_note_to_property)
from app.keyboards.inline_keyboards import (get_edit_property_keyboard, get_region_keyboard,
                                           get_district_keyboard, get_rooms_keyboard,
                                           get_guests_keyboard, get_property_types_keyboard,
                                           get_media_management_keyboard, get_delete_one_media_keyboard,
                                           get_finish_upload_keyboard, get_skip_video_keyboard,
                                           get_calendar)
from .manage_property import my_properties_list
from app.core.constants import DISTRICTS

router = Router()


# --- Вспомогательные функции ---

async def show_edit_menu(message_or_callback: Message | CallbackQuery, state: FSMContext, message_text: str | None = None):
    data = await state.get_data()
    property_id = data.get('property_id')

    if not property_id:
        logging.error("Не найден property_id в состоянии FSM при попытке показать меню редактирования.")
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("Произошла ошибка, попробуйте снова.", show_alert=True)
        else:
            await message_or_callback.answer("Произошла ошибка, попробуйте снова.")
        await state.clear()
        return

    prop, _, _ = await get_property_with_media_and_owner(property_id)
    if not prop:
        await message_or_callback.answer("Не удалось найти объект. Возможно, он был удален.")
        await state.clear()
        return

    text = message_text or f"Редактирование объекта: **{prop.title}**\n\nЧто вы хотите изменить?"
    keyboard = get_edit_property_keyboard(property_id)

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=keyboard)
    else:
        try:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logging.warning(f"Не удалось отредактировать сообщение в show_edit_menu: {e}")
            await message_or_callback.answer()


    await state.set_state(EditProperty.choosing_field)


async def start_media_management(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    property_id = data.get('property_id')
    prop, _, _ = await get_property_with_media_and_owner(property_id)

    await callback_query.message.delete()
    await callback_query.message.answer("Управление медиафайлами:")
    if not prop.media:
        await callback_query.message.answer("У этого объекта еще нет фото или видео.")
    else:
        await callback_query.message.answer("Текущие медиафайлы. Нажмите на 🗑️ под каждым, чтобы удалить.")
        for media in prop.media:
            if media.media_type == 'photo':
                await callback_query.message.answer_photo(media.file_id, reply_markup=get_delete_one_media_keyboard(media.id))
            elif media.media_type == 'video_note':
                await callback_query.message.answer_video_note(media.file_id, reply_markup=get_delete_one_media_keyboard(media.id))

    await callback_query.message.answer("Выберите дальнейшее действие:", reply_markup=get_media_management_keyboard(property_id))
    await state.set_state(EditProperty.managing_media)

# --- Начало диалога ---

@router.callback_query(F.data.startswith("manage:edit:"))
async def start_property_edit(callback: CallbackQuery, state: FSMContext):
    property_id = int(callback.data.split(":")[2])
    await state.update_data(property_id=property_id)
    await show_edit_menu(callback, state)
    await callback.answer()

# --- Главный диспетчер меню редактирования ---
@router.callback_query(EditProperty.choosing_field, F.data.startswith("edit_prop:"))
async def edit_field_prompt(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    field = parts[1]

    if field == 'media':
        await start_media_management(callback, state)
        await callback.answer()
        return
    elif field == 'availability':
        await start_availability_management(callback, state)
        return

    prompts = {
        "title": ("Введите новое название:", EditProperty.editing_title),
        "description": ("Введите новое описание:", EditProperty.editing_description),
        "address": ("Введите новый адрес:", EditProperty.editing_address),
        "price": ("Введите новую цену за ночь (только цифры):", EditProperty.editing_price),
        "location": ("Выберите новый регион:", EditProperty.editing_region),
        "rooms": ("Выберите новое кол-во комнат:", EditProperty.editing_rooms),
        "guests": ("Выберите новое кол-во гостей:", EditProperty.editing_guests),
        "type": ("Выберите новый тип объекта:", EditProperty.editing_type),
    }

    if field in prompts:
        prompt_text, new_state = prompts[field]
        keyboard = None
        if field == 'location': keyboard = get_region_keyboard()
        if field == 'rooms': keyboard = get_rooms_keyboard()
        if field == 'guests': keyboard = get_guests_keyboard()
        if field == 'type': keyboard = get_property_types_keyboard()

        await callback.message.edit_text(prompt_text, reply_markup=keyboard)
        await state.set_state(new_state)

    await callback.answer()

# --- Обработка новых значений ---

@router.message(StateFilter(EditProperty.editing_title, EditProperty.editing_description, EditProperty.editing_address))
async def process_new_text_field(message: Message, state: FSMContext):
    current_state_str = await state.get_state()
    field_map = {
        EditProperty.editing_title.state: 'title',
        EditProperty.editing_description.state: 'description',
        EditProperty.editing_address.state: 'address',
    }
    field_to_update = field_map[current_state_str]

    data = await state.get_data()
    await update_property_field(data['property_id'], field_to_update, message.text)

    await message.answer(f"Поле '{field_to_update.replace('_', ' ').capitalize()}' успешно обновлено!")
    await show_edit_menu(message, state)

@router.message(EditProperty.editing_price)
async def process_new_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите цену цифрами.")
        return
    data = await state.get_data()
    await update_property_field(data['property_id'], 'price_per_night', int(message.text))
    await message.answer("Цена успешно обновлена!")
    await show_edit_menu(message, state)

@router.callback_query(StateFilter(EditProperty.editing_rooms, EditProperty.editing_guests, EditProperty.editing_type))
async def process_new_button_field(callback: CallbackQuery, state: FSMContext):
    current_state_str = await state.get_state()
    field_map = {
        EditProperty.editing_rooms.state: ('rooms', 'add_property_rooms:'),
        EditProperty.editing_guests.state: ('max_guests', 'add_property_guests:'),
        EditProperty.editing_type.state: ('property_type', 'add_property_type:'),
    }
    field_to_update, prefix = field_map[current_state_str]
    value = callback.data.replace(prefix, '')

    if field_to_update == 'rooms':
        value_to_save = 0 if value == 'Студия' else int(value.replace('+', ''))
    elif field_to_update == 'max_guests':
        value_to_save = int(value.replace('+', ''))
    else:
        value_to_save = value

    data = await state.get_data()
    await update_property_field(data['property_id'], field_to_update, value_to_save)

    await callback.message.answer(f"Поле '{field_to_update.replace('_', ' ').capitalize()}' успешно обновлено!")
    await show_edit_menu(callback, state)
    await callback.answer()

@router.callback_query(EditProperty.editing_region, F.data.startswith("add_property_region:"))
async def process_new_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split(":")[1]
    if region == "Куршская коса":
        data = await state.get_data()
        await update_property_field(data['property_id'], 'district', region)
        await callback.message.answer("Район успешно обновлен!")
        await show_edit_menu(callback, state)
    else:
        await callback.message.edit_text("Уточните локацию:", reply_markup=get_district_keyboard(region))
        await state.set_state(EditProperty.editing_district)
    await callback.answer()

@router.callback_query(EditProperty.editing_district, F.data.startswith("add_prop_dist:"))
async def process_new_district(callback: CallbackQuery, state: FSMContext):
    _, region, district_index_str = callback.data.split(":")
    district_index = int(district_index_str)
    district_name = DISTRICTS[region][district_index]
    data = await state.get_data()
    await update_property_field(data['property_id'], 'district', district_name)
    await callback.message.answer("Район успешно обновлен!")
    await show_edit_menu(callback, state)
    await callback.answer()

# --- УПРАВЛЕНИЕ ДОСТУПНОСТЬЮ ---

async def _show_availability_calendar(callback: CallbackQuery, state: FSMContext):
    property_id = (await state.get_data())['property_id']
    
    manual_unavailable = await availability_service.get_unavailable_dates(property_id)
    booked_dates = await booking_service.get_booked_dates_for_property(property_id)
    all_unavailable_dates = sorted(list(set(manual_unavailable + booked_dates)))

    text = "🗓️ **Управление доступностью**\n\n"
    if all_unavailable_dates:
        dates_str = ", ".join([d.strftime("%d.%m") for d in all_unavailable_dates])
        text += f"🚫 **Занятые даты (брони + блокировки):**\n`{dates_str}`\n\n"
    
    text += "Нажмите на дату для ручной блокировки/разблокировки. Нажмите 'Готово', когда закончите."

    calendar_keyboard = await get_calendar()
    builder = InlineKeyboardBuilder.from_markup(calendar_keyboard)
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="availability:done"))
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception as e:
        logging.info(f"Не удалось обновить календарь (сообщение не изменилось): {e}")
        await callback.answer()

async def start_availability_management(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(EditProperty.managing_availability)
    await _show_availability_calendar(callback, state)

@router.callback_query(EditProperty.managing_availability, SimpleCalendarCallback.filter())
async def process_availability_date(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    calendar = SimpleCalendar()
    selected, date_obj = await calendar.process_selection(callback, callback_data)

    if selected:
        property_id = (await state.get_data())['property_id']
        selected_date = date_obj.date()

        if selected_date < date.today():
            await callback.answer("Нельзя изменить прошедшую дату.", show_alert=True)
            return
        
        booked_dates = await booking_service.get_booked_dates_for_property(property_id)
        if selected_date in booked_dates:
            await callback.answer("Эту дату нельзя изменить, она занята подтвержденной бронью.", show_alert=True)
            return

        manual_unavailable = await availability_service.get_unavailable_dates(property_id)
        if selected_date in manual_unavailable:
            await availability_service.remove_unavailable_date(property_id, selected_date)
            await callback.answer(f"Дата {selected_date.strftime('%d.%m.%Y')} разблокирована.")
        else:
            await availability_service.add_unavailable_date(property_id, selected_date)
            await callback.answer(f"Дата {selected_date.strftime('%d.%m.%Y')} заблокирована.")
            
        await _show_availability_calendar(callback, state)
    else:
        # Для навигации просто перерисовываем календарь
        await _show_availability_calendar(callback, state)

@router.callback_query(EditProperty.managing_availability, F.data == "availability:done")
async def finish_availability_management(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Настройки сохранены")
    await show_edit_menu(callback, state, message_text="Настройки доступности сохранены.")

# --- Управление медиафайлами ---

@router.callback_query(EditProperty.managing_media, F.data.startswith("edit_media:delete:"))
async def delete_media_item_handler(callback: CallbackQuery):
    media_id = int(callback.data.split(":")[2])
    await delete_one_media_item(media_id)
    await callback.message.delete()
    await callback.answer("Медиафайл удален.", show_alert=True)

@router.callback_query(EditProperty.managing_media, F.data.startswith("edit_media:add:"))
async def add_more_media_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Отправьте новые фото (до 10) или видео-кружочек. Когда закончите, нажмите кнопку.",
        reply_markup=get_finish_upload_keyboard()
    )
    await state.set_state(EditProperty.adding_photos)
    await callback.answer()

@router.message(StateFilter(EditProperty.adding_photos), F.photo)
async def handle_new_photos_in_edit(message: Message, state: FSMContext):
    photos = (await state.get_data()).get('photos_to_add', [])
    if len(photos) >= 10:
        await message.answer("Вы уже добавили 10 фото. Нажмите 'Завершить загрузку'.")
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos_to_add=photos)

@router.message(StateFilter(EditProperty.adding_photos), F.video_note)
async def handle_new_video_in_edit(message: Message, state: FSMContext):
    await state.update_data(video_to_add=message.video_note.file_id)
    await message.answer("Кружочек получен. Вы можете отправить еще фото или нажать 'Завершить загрузку'.")

@router.message(StateFilter(EditProperty.adding_photos), F.text == "Завершить загрузку")
async def finish_adding_photos_in_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos_to_add')
    video = data.get('video_to_add')
    property_id = data.get('property_id')
    if not photos and not video:
        await message.answer("Вы не отправили ни одного файла. Нажмите 'Отмена' для выхода.", reply_markup=ReplyKeyboardRemove())
        await show_edit_menu(message, state)
        return

    if photos: await add_photos_to_property(property_id, photos)
    if video: await add_video_note_to_property(property_id, video)
    
    await message.answer("Новые медиафайлы добавлены!", reply_markup=ReplyKeyboardRemove())
    await state.update_data(photos_to_add=[], video_to_add=None)
    await show_edit_menu(message, state)

# --- Выход и Отмена ---

@router.callback_query(StateFilter(EditProperty.managing_media), F.data.startswith("edit_media:done:"))
async def finish_media_management(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await show_edit_menu(callback, state)
    await callback.answer()

@router.callback_query(EditProperty.choosing_field, F.data == "back_to_my_properties")
async def back_to_list_from_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await my_properties_list(callback.message)
    await callback.answer("Вы вышли из режима редактирования.")

@router.message(StateFilter(EditProperty), Command("cancel"))
@router.message(StateFilter(EditProperty), F.text.casefold() == "отмена")
async def cancel_edit_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Редактирование отменено.", reply_markup=ReplyKeyboardRemove())
