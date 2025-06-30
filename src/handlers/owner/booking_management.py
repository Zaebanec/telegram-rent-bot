from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery
from src.services.repository import update_booking_status, get_booking_with_details

router = Router()

@router.callback_query(F.data.startswith("booking:confirm:"))
async def confirm_booking(callback: CallbackQuery, bot: Bot):
    booking_id = int(callback.data.split(":")[2])
    
    # Обновляем статус в БД и получаем обновленную запись
    booking = await update_booking_status(booking_id, "confirmed")
    if not booking:
        await callback.answer("Бронирование не найдено.", show_alert=True)
        return

    # Убираем кнопки и пишем, что заявка принята
    await callback.message.edit_text(f"{callback.message.text}\n\n--- \n✅ ВЫ ПРИНЯЛИ ЭТУ ЗАЯВКУ ---")
    
    # Отправляем уведомление арендатору
    try:
        await bot.send_message(
            chat_id=booking.user.telegram_id,
            text=f"🎉 Ваша заявка на бронирование объекта «{booking.property.title}» была ОДОБРЕНА!\n\nВладелец скоро свяжется с вами для уточнения деталей."
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление арендатору: {e}")
        
    await callback.answer("Вы успешно приняли заявку!")


@router.callback_query(F.data.startswith("booking:reject:"))
async def reject_booking(callback: CallbackQuery, bot: Bot):
    booking_id = int(callback.data.split(":")[2])
    
    booking = await update_booking_status(booking_id, "rejected")
    if not booking:
        await callback.answer("Бронирование не найдено.", show_alert=True)
        return

    await callback.message.edit_text(f"{callback.message.text}\n\n--- \n❌ ВЫ ОТКЛОНИЛИ ЭТУ ЗАЯВКУ ---")

    try:
        await bot.send_message(
            chat_id=booking.user.telegram_id,
            text=f"😔 К сожалению, ваша заявка на бронирование объекта «{booking.property.title}» была ОТКЛОНЕНА."
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление арендатору: {e}")
        
    await callback.answer("Вы отклонили заявку.")