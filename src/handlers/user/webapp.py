import json
from datetime import datetime
from aiogram import F, Router, Bot
from aiogram.types import Message

from src.services.property_service import get_property_with_media_and_owner
from src.services import booking_service
from src.keyboards.inline_keyboards import get_booking_management_keyboard

# Создаем отдельный роутер специально для Web App
router = Router()

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
        total_price = data['total_price']

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
        
        await message.answer("✅ Спасибо! Ваша заявка на бронирование отправлена владельцу. Он скоро с вами свяжется.")

    except Exception as e:
        print(f"Ошибка обработки данных из Web App: {e}")
        await message.answer("Произошла ошибка при обработке вашего бронирования. Попробуйте снова.")