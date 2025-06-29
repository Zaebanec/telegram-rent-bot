import logging
from aiogram import F, Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (Message, CallbackQuery, ReplyKeyboardRemove)

from app.utils.states import EditProperty
from app.services.property_service import get_property_with_media_and_owner, update_property_field
from app.services.media_service import (delete_one_media_item, add_photos_to_property,
                                        add_video_note_to_property)
# Импортируем все необходимые клавиатуры
from app.keyboards.inline_keyboards import (get_edit_property_keyboard, get_region_keyboard,
                                           get_district_keyboard, get_rooms_keyboard,
                                           get_guests_keyboard, get_property_types_keyboard,
                                           get_media_management_keyboard, get_delete_one_media_keyboard,
                                           get_finish_upload_keyboard)
# Импортируем обработчик /myproperties, чтобы вернуться к нему после редактирования
from .manage_property import my_properties_list
from app.core.constants import DISTRICTS

router = Router()


# --- Вспомогательные функции ---

async def show_edit_menu(message_or_callback: Message | CallbackQuery, state: FSMContext, message_text: str | None = None):
    """
    Отображает главное меню редактирования объекта.
    Эта функция вызывается каждый раз после успешного изменения поля.
    """
    data = await state.get_data()
    property_id = data.get('property_id')

    if not property_id:
        # Критическая ошибка, если мы потеряли ID объекта в состоянии
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

    # Формируем текст и клавиатуру для меню
    text = message_text or f"Редактирование объекта: **{prop.title}**\n\nЧто вы хотите изменить?"
    keyboard = get_edit_property_keyboard(property_id)

    # Отправляем или редактируем сообщение
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=keyboard)
    else:
        try:
            # Пытаемся отредактировать, чтобы не было "прыгающих" сообщений
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            # Если не получилось (например, текст не изменился), просто отвечаем на колбэк
            logging.warning(f"Не удалось отредактировать сообщение в show_edit_menu: {e}")
            await message_or_callback.answer()

    # Устанавливаем состояние ожидания выбора поля для редактирования
    await state.set_state(EditProperty.choosing_field)


async def start_media_management(callback_query: CallbackQuery, state: FSMContext):
    """
    Запускает интерфейс управления медиафайлами (фото и видео).
    """
    data = await state.get_data()
    property_id = data.get('property_id')
    prop, _, _ = await get_property_with_media_and_owner(property_id)

    # Удаляем предыдущее сообщение с меню, чтобы не было мусора
    await callback_query.message.delete()
    await callback_query.message.answer("Управление медиафайлами:")
    if not prop.media:
        await callback_query.message.answer("У этого объекта еще нет фото или видео.")
    else:
        # Выводим все текущие медиафайлы с кнопкой удаления под каждым
        await callback_query.message.answer("Текущие медиафайлы. Нажмите на 🗑️ под каждым, чтобы удалить.")
        for media in prop.media:
            if media.media_type == 'photo':
                await callback_query.message.answer_photo(media.file_id, reply_markup=get_delete_one_media_keyboard(media.id))
            elif media.media_type == 'video_note':
                await callback_query.message.answer_video_note(media.file_id, reply_markup=get_delete_one_media_keyboard(media.id))

    # Показываем клавиатуру с действиями: добавить еще или завершить
    await callback_query.message.answer("Выберите дальнейшее действие:", reply_markup=get_media_management_keyboard(property_id))
    await state.set_state(EditProperty.managing_media)

# --- Начало диалога редактирования ---

@router.callback_query(F.data.startswith("manage:edit:"))
async def start_property_edit(callback: CallbackQuery, state: FSMContext):
    """
    Точка входа в режим редактирования. Срабатывает по кнопке 'Редактировать'.
    """
    property_id = int(callback.data.split(":")[2])
    # Сохраняем ID объекта в FSM для дальнейшего использования
    await state.update_data(property_id=property_id)
    # Показываем главное меню редактирования
    await show_edit_menu(callback, state)
    await callback.answer()

# --- Главный диспетчер меню редактирования ---

@router.callback_query(EditProperty.choosing_field, F.data.startswith("edit_prop:"))
async def edit_field_prompt(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор поля для редактирования из главного меню.
    """
    parts = callback.data.split(":")
    field = parts[1]

    # Особые случаи для медиа и доступности, которые открывают свои интерфейсы
    if field == 'media':
        await start_media_management(callback, state)
        await callback.answer()
        return

    # Словарь с подсказками и состояниями для каждого поля
    prompts = {
        "title": ("Введите новое название:", EditProperty.editing_title),
        "description": ("Введите новое описание:", EditProperty.editing_description),
        "address": ("Введите новый адрес:", EditProperty.editing_address),
        "price": ("Введите новую цену за ночь (только цифры):", EditProperty.editing_price),
        "rooms": ("Выберите новое кол-во комнат:", EditProperty.editing_rooms),
        "guests": ("Выберите новое кол-во гостей:", EditProperty.editing_guests),
        "type": ("Выберите новый тип объекта:", EditProperty.editing_type),
    }

    if field in prompts:
        prompt_text, new_state = prompts[field]
        # Для некоторых полей нужна клавиатура выбора
        keyboard = None
        if field == 'rooms': keyboard = get_rooms_keyboard()
        if field == 'guests': keyboard = get_guests_keyboard()
        if field == 'type': keyboard = get_property_types_keyboard()

        await callback.message.edit_text(prompt_text, reply_markup=keyboard)
        await state.set_state(new_state)

    await callback.answer()

# --- Обработка новых значений от пользователя ---

@router.message(StateFilter(EditProperty.editing_title, EditProperty.editing_description, EditProperty.editing_address))
async def process_new_text_field(message: Message, state: FSMContext):
    """Обрабатывает ввод нового текстового значения (название, описание, адрес)."""
    current_state_str = await state.get_state()
    field_map = {
        EditProperty.editing_title.state: 'title',
        EditProperty.editing_description.state: 'description',
        EditProperty.editing_address.state: 'address',
    }
    field_to_update = field_map[current_state_str]

    data = await state.get_data()
    # Вызываем сервис для обновления поля в БД
    await update_property_field(data['property_id'], field_to_update, message.text)

    await message.answer(f"Поле '{field_to_update.replace('_', ' ').capitalize()}' успешно обновлено!")
    # Возвращаемся в главное меню редактирования
    await show_edit_menu(message, state)

@router.message(EditProperty.editing_price)
async def process_new_price(message: Message, state: FSMContext):
    """Обрабатывает ввод новой цены."""
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите цену цифрами.")
        return
    data = await state.get_data()
    await update_property_field(data['property_id'], 'price_per_night', int(message.text))
    await message.answer("Цена успешно обновлена!")
    await show_edit_menu(message, state)

@router.callback_query(StateFilter(EditProperty.editing_rooms, EditProperty.editing_guests, EditProperty.editing_type))
async def process_new_button_field(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор нового значения с инлайн-кнопок (комнаты, гости, тип)."""
    current_state_str = await state.get_state()
    field_map = {
        EditProperty.editing_rooms.state: ('rooms', 'add_property_rooms:'),
        EditProperty.editing_guests.state: ('max_guests', 'add_property_guests:'),
        EditProperty.editing_type.state: ('property_type', 'add_property_type:'),
    }
    field_to_update, prefix = field_map[current_state_str]
    value = callback.data.replace(prefix, '')

    # Преобразуем строковые значения в числовые для БД
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

# --- Управление медиафайлами (в режиме редактирования) ---

@router.callback_query(EditProperty.managing_media, F.data.startswith("edit_media:delete:"))
async def delete_media_item_handler(callback: CallbackQuery):
    """Удаляет один медиафайл по кнопке под ним."""
    media_id = int(callback.data.split(":")[2])
    await delete_one_media_item(media_id)
    # Просто удаляем сообщение с этим медиа
    await callback.message.delete()
    await callback.answer("Медиафайл удален.", show_alert=True)

@router.callback_query(EditProperty.managing_media, F.data.startswith("edit_media:add:"))
async def add_more_media_prompt(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс добавления новых медиафайлов."""
    await callback.message.answer(
        "Отправьте новые фото (до 10) или видео-кружочек. Когда закончите, нажмите кнопку.",
        reply_markup=get_finish_upload_keyboard()
    )
    await state.set_state(EditProperty.adding_photos)
    await callback.answer()

@router.message(StateFilter(EditProperty.adding_photos), F.photo)
async def handle_new_photos_in_edit(message: Message, state: FSMContext):
    """Ловит новые фотографии в режиме добавления."""
    photos = (await state.get_data()).get('photos_to_add', [])
    if len(photos) >= 10:
        await message.answer("Вы уже добавили 10 фото. Нажмите 'Завершить загрузку'.")
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos_to_add=photos)

@router.message(StateFilter(EditProperty.adding_photos), F.text == "Завершить загрузку")
async def finish_adding_photos_in_edit(message: Message, state: FSMContext):
    """Завершает процесс добавления новых фото, сохраняет их в БД."""
    data = await state.get_data()
    photos = data.get('photos_to_add')
    property_id = data.get('property_id')
    if not photos:
        await message.answer("Вы не отправили ни одного файла. Нажмите 'Отмена' для выхода.", reply_markup=ReplyKeyboardRemove())
        await show_edit_menu(message, state)
        return

    await add_photos_to_property(property_id, photos)
    
    await message.answer("Новые фото добавлены!", reply_markup=ReplyKeyboardRemove())
    # Очищаем временное хранилище фото и возвращаемся в меню
    await state.update_data(photos_to_add=[])
    await show_edit_menu(message, state)

# --- Выход и Отмена ---

@router.callback_query(StateFilter(EditProperty.managing_media), F.data.startswith("edit_media:done:"))
async def finish_media_management(callback: CallbackQuery, state: FSMContext):
    """Выход из режима управления медиа в главное меню редактирования."""
    await callback.message.delete()
    await show_edit_menu(callback, state)
    await callback.answer()

@router.callback_query(EditProperty.choosing_field, F.data == "back_to_my_properties")
async def back_to_list_from_edit(callback: CallbackQuery, state: FSMContext):
    """Выход из режима редактирования в общий список объектов /myproperties."""
    await state.clear()
    await callback.message.delete()
    # Вызываем хендлер команды /myproperties, чтобы показать актуальный список
    await my_properties_list(callback.message)
    await callback.answer("Вы вышли из режима редактирования.")

@router.message(StateFilter(EditProperty), Command("cancel"))
@router.message(StateFilter(EditProperty), F.text.casefold() == "отмена")
async def cancel_edit_handler(message: Message, state: FSMContext):
    """Отмена любого шага редактирования по команде /cancel или слову 'отмена'."""
    await state.clear()
    await message.answer("Редактирование отменено.", reply_markup=ReplyKeyboardRemove())