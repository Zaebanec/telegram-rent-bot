import logging
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

from src.utils.states import AddProperty
from src.services.user_service import get_user
from src.services.property_service import add_property
from src.services.media_service import add_photos_to_property, add_video_note_to_property

# --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Указываем единственно верный файл с клавиатурами ---
from src.keyboards.inline_keyboards import (get_region_keyboard, get_district_keyboard, get_rooms_keyboard, 
                                           get_property_types_keyboard, get_guests_keyboard, 
                                           get_finish_upload_keyboard, get_skip_video_keyboard)
from src.core.constants import DISTRICTS

router = Router()

# --- Начало диалога ---
@router.callback_query(F.data == "main_menu:add_property")
async def add_property_callback(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    if not user or user.role not in ['owner', 'admin']:
        await callback.answer("Эта функция доступна только владельцам объектов.", show_alert=True)
        return
        
    await callback.message.edit_text("Начинаем. Введите броское название вашего объекта (например, 'Лофт с видом на Кафедральный собор').")
    await state.set_state(AddProperty.title)
    await callback.answer()

@router.message(Command("addproperty"))
async def add_property_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or user.role not in ['owner', 'admin']:
        await message.answer("Эта функция доступна только владельцам объектов.")
        return
        
    await message.answer("Начинаем. Введите броское название вашего объекта (например, 'Лофт с видом на Кафедральный собор').")
    await state.set_state(AddProperty.title)


# --- Основная цепочка диалога ---

@router.message(AddProperty.title)
async def add_property_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Отлично. Теперь добавьте яркое описание, расскажите о преимуществах.")
    await state.set_state(AddProperty.description)

@router.message(AddProperty.description)
async def add_property_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Теперь выберите, где находится ваш объект:", reply_markup=get_region_keyboard())
    await state.set_state(AddProperty.region)

@router.callback_query(AddProperty.region, F.data.startswith("add_property_region:"))
async def add_property_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split(":")[1]
    await state.update_data(region=region)
    if region == "Куршская коса":
        await state.update_data(district=region)
        await callback.message.edit_text("Принято. Теперь введите точный адрес (поселок, улица, дом).")
        await state.set_state(AddProperty.address)
    else:
        await callback.message.edit_text("Уточните локацию:", reply_markup=get_district_keyboard(region))
        await state.set_state(AddProperty.district)
    await callback.answer()

@router.callback_query(AddProperty.district, F.data == "back_to_regions")
async def back_to_regions(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите, где находится ваш объект:", reply_markup=get_region_keyboard())
    await state.set_state(AddProperty.region)
    await callback.answer()

@router.callback_query(AddProperty.district, F.data.startswith("add_prop_dist:"))
async def add_property_district(callback: CallbackQuery, state: FSMContext):
    _, region, district_index_str = callback.data.split(":")
    district_index = int(district_index_str)
    district_name = DISTRICTS[region][district_index]
    await state.update_data(district=district_name)
    await callback.message.edit_text("Принято. Теперь введите точный адрес (улица, дом).")
    await state.set_state(AddProperty.address)
    await callback.answer()

@router.message(AddProperty.address)
async def add_property_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Укажите количество комнат:", reply_markup=get_rooms_keyboard())
    await state.set_state(AddProperty.rooms)
    
@router.callback_query(AddProperty.rooms, F.data.startswith("add_property_rooms:"))
async def add_property_rooms(callback: CallbackQuery, state: FSMContext):
    rooms = callback.data.split(":")[1]
    await state.update_data(rooms=rooms)
    await callback.message.edit_text("Супер. Укажите цену за ночь в рублях (только цифры).")
    await state.set_state(AddProperty.price_per_night)
    await callback.answer()

@router.message(AddProperty.price_per_night)
async def add_property_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите цену цифрами.")
        return
    await state.update_data(price_per_night=message.text)
    await message.answer("Хорошо. Теперь выберите максимальное количество гостей:", reply_markup=get_guests_keyboard())
    await state.set_state(AddProperty.max_guests)

@router.callback_query(AddProperty.max_guests, F.data.startswith("add_property_guests:"))
async def add_property_guests(callback: CallbackQuery, state: FSMContext):
    guests = callback.data.split(":")[1]
    await state.update_data(max_guests=guests)
    await callback.message.edit_text("И последнее: выберите тип объекта:", reply_markup=get_property_types_keyboard())
    await state.set_state(AddProperty.property_type)
    await callback.answer()

@router.callback_query(AddProperty.property_type, F.data.startswith("add_property_type:"))
async def add_property_type_final(callback: CallbackQuery, state: FSMContext):
    property_type = callback.data.split(":")[1]
    await state.update_data(property_type=property_type)
    data = await state.get_data()
    
    try:
        property_id = await add_property(data, owner_id=callback.from_user.id)
        await state.update_data(property_id=property_id)
        
        await callback.message.edit_text("Текстовая информация сохранена.")
        await callback.message.answer(
            "Теперь отправьте мне от 1 до 10 фотографий вашего объекта. "
            "Можно отправить их одним альбомом. Когда закончите, нажмите кнопку 'Завершить загрузку'.",
            reply_markup=get_finish_upload_keyboard()
        )
        await state.set_state(AddProperty.photos)
    except Exception as e:
        logging.error(f"Ошибка при добавлении объекта в БД: {e}")
        await callback.message.answer("К сожалению, при сохранении произошла ошибка.")
        await state.clear()
    finally:
        await callback.answer()

@router.message(AddProperty.photos, F.photo)
async def handle_photos(message: Message, state: FSMContext):
    photos = (await state.get_data()).get('photos', [])
    if len(photos) >= 10:
        await message.answer("Вы уже загрузили максимальное количество фотографий (10). Нажмите 'Завершить загрузку'.")
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)

@router.message(AddProperty.photos, F.text == "Завершить загрузку")
async def finish_photo_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos')
    property_id = data.get('property_id')

    if not photos:
        await message.answer("Вы не загрузили ни одной фотографии. Пожалуйста, отправьте хотя бы одну или отмените /cancel")
        return

    try:
        await add_photos_to_property(property_id, photos)
        await message.answer(
            "Фотографии сохранены. Теперь, если хотите, запишите и отправьте короткий видео-тур ('кружочек') по объекту. Это сильно повысит доверие. Или пропустите этот шаг.",
            reply_markup=get_skip_video_keyboard()
        )
        await state.set_state(AddProperty.video_note)
    except Exception as e:
        logging.error(f"Ошибка при сохранении фото в БД: {e}")
        await message.answer("Произошла ошибка при сохранении фотографий. Пожалуйста, попробуйте позже.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        
@router.message(AddProperty.video_note, F.video_note)
async def handle_video_note(message: Message, state: FSMContext):
    data = await state.get_data()
    property_id = data.get('property_id')
    
    try:
        await add_video_note_to_property(property_id, message.video_note.file_id)
        await message.answer(
            "<b>Отлично! Ваш объект с фото и видео-туром успешно добавлен!</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении видео в БД: {e}")
        await message.answer("Произошла ошибка при сохранении видео. Пожалуйста, попробуйте позже.", reply_markup=ReplyKeyboardRemove())
    finally:
        await state.clear()

@router.message(AddProperty.video_note, F.text.in_({"Пропустить этот шаг", "Отмена"}))
async def skip_video_note(message: Message, state: FSMContext):
    await message.answer(
        "<b>Хорошо! Ваш объект с фотографиями успешно добавлен!</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()
    
@router.message(AddProperty.photos)
async def incorrect_photo_upload(message: Message):
    await message.answer(
        "Пожалуйста, отправьте фотографию или нажмите кнопку 'Завершить загрузку' / 'Отмена'.",
        reply_markup=get_finish_upload_keyboard()
    )
    
@router.message(AddProperty.video_note)
async def incorrect_video_upload(message: Message):
    await message.answer(
        "Пожалуйста, отправьте видео-сообщение ('кружочек') или нажмите кнопку 'Пропустить этот шаг' / 'Отмена'.",
        reply_markup=get_skip_video_keyboard()
    )

@router.message(StateFilter(AddProperty), Command("cancel"))
@router.message(StateFilter(AddProperty), F.text.casefold() == "отмена")
async def cancel_add_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=ReplyKeyboardRemove())