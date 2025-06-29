import json
from datetime import datetime, timedelta
from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from app.services.property_service import get_property_with_media_and_owner
from app.services import booking_service
from app.services.review_service import get_reviews_summary
from app.keyboards.inline_keyboards import (get_booking_management_keyboard, 
                                            get_property_card_keyboard)

router = Router()


@router.callback_query(F.data.startswith(("view_photos:", "view_media:")))
async def view_media(callback: CallbackQuery, bot: Bot):
    """
    Обработчик для кнопок "📸 Все фото" и "▶️ Видео и фото".
    Отправляет пользователю все медиафайлы, связанные с объектом.
    """
    await callback.answer()  # Отвечаем на колбэк, чтобы убрать "часики"
    property_id = int(callback.data.split(":")[1])

    # Получаем объект, его фото и видео из сервисного слоя
    prop, photo_files, video_file = await get_property_with_media_and_owner(property_id)

    if not prop:
        await callback.message.answer("Объект не найден.")
        return

    media_to_show = []
    # Если есть видео и пользователь нажал "Видео и фото", отправляем видео отдельно
    if video_file and callback.data.startswith("view_media:"):
        await bot.send_video_note(chat_id=callback.from_user.id, video_note=video_file)
        # После видео покажем все фото
        media_to_show = photo_files
    # Если пользователь нажал "Все фото", показываем все фото, кроме первого (оно уже есть в карточке)
    elif callback.data.startswith("view_photos:") and len(photo_files) > 1:
        media_to_show = photo_files[1:]

    # Отправляем фотографии
    if media_to_show:
        # Если фото больше одного, отправляем их как альбом
        if len(media_to_show) > 1:
            media_group = [InputMediaPhoto(media=file_id) for file_id in media_to_show]
            await bot.send_media_group(chat_id=callback.from_user.id, media=media_group)
        # Если фото только одно, отправляем его как обычное фото
        elif len(media_to_show) == 1:
            await bot.send_photo(chat_id=callback.from_user.id, photo=media_to_show[0])
    elif not video_file:
         # Если пользователь нажал на кнопку, а других фото нет
         await callback.message.answer("Больше фотографий нет.")


# --- Обработчик для данных из Web App (остается без изменений) ---
@router.message(F.web_app_data)
async def process_booking_from_webapp(message: Message, bot: Bot):
    """
    Этот хендлер "ловит" данные, отправленные из Web App календаря.
    """
    try:
        data = json.loads(message.web_app_data.data)
        
        property_id = int(data['property_id'])
        checkin_date = datetime.fromisoformat(data['checkin_date'])
        checkout_date = datetime.fromisoformat(data['checkout_date'])

        prop, _, _ = await get_property_with_media_and_owner(property_id)
        if not prop:
            await message.answer("Ошибка: объект не найден.")
            return

        if prop.owner.telegram_id == message.from_user.id:
            await message.answer("Вы не можете забронировать свой собственный объект.")
            return

        new_booking = await booking_service.create_booking(
            user_id=message.from_user.id,
            property_id=property_id,
            start_date=checkin_date,
            end_date=checkout_date
        )

        user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        num_nights = (checkout_date - checkin_date).days
        total_price = data['total_price'] # Берем цену из WebApp

        await bot.send_message(
            chat_id=prop.owner.telegram_id,
            text=(
                f"🔔 Новая заявка на бронирование!\n\n"
                f"<b>Объект:</b> «{prop.title}»\n"
                f"<b>Даты:</b> с {checkin_date.strftime('%d.%m.%Y')} по {checkout_date.strftime('%d.%m.%Y')} ({num_nights} ночей)\n"
                f"<b>Сумма:</b> {total_price} руб.\n"
                f"<b>Гость:</b> {user_info}"
            ),
            reply_markup=get_booking_management_keyboard(new_booking.id)
        )
        
        await message.answer("✅ Спасибо! Ваша заявка на бронирование отправлена владельцу.")

    except Exception as e:
        print(f"Ошибка обработки данных из Web App: {e}")
        await message.answer("Произошла ошибка при обработке вашего бронирования. Попробуйте снова.")