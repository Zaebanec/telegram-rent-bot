import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

# --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Обновляем импорты ---
from app.services.property_service import set_property_verified
from app.services.booking_service import update_booking_status, get_booking_with_details
from app.services.user_service import set_user_role
from app.core.settings import settings
from app.core.scheduler import scheduler, request_review

router = Router()
# Фильтр гарантирует, что все обработчики в этом файле будут работать только для админов
router.message.filter(F.from_user.id.in_(settings.ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(settings.ADMIN_IDS))


@router.message(Command("setrole"))
async def set_user_role_handler(message: Message):
    """
    Устанавливает роль пользователю.
    Формат: /setrole <user_id> <role>
    Роли: user, owner, admin
    """
    try:
        parts = message.text.split()
        if len(parts) != 3: raise ValueError()
        
        user_id = int(parts[1])
        role = parts[2].lower()

        if role not in ['user', 'owner', 'admin']:
            await message.answer("Неверная роль. Доступные роли: user, owner, admin.")
            return

        await set_user_role(user_id, role)
        await message.answer(f"Пользователю с ID {user_id} была успешно присвоена роль '{role}'.")

    except (IndexError, ValueError):
        await message.answer("Неверный формат команды. Используйте: /setrole <ID> <роль>")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")


@router.message(Command("verify"))
async def verify_property(message: Message):
    """
    Верифицирует объект по ID.
    Формат: /verify 123
    """
    try:
        property_id = int(message.text.split()[1])
        await set_property_verified(property_id, status=True)
        await message.answer(f"Объект с ID {property_id} был успешно верифицирован ✅.")
    except (IndexError, ValueError):
        await message.answer("Неверный формат команды. Используйте: /verify <ID объекта>")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")

@router.message(Command("unverify"))
async def unverify_property(message: Message):
    """
    Снимает верификацию с объекта по ID.
    Формат: /unverify 123
    """
    try:
        property_id = int(message.text.split()[1])
        await set_property_verified(property_id, status=False)
        await message.answer(f"С объекта с ID {property_id} была снята верификация.")
    except (IndexError, ValueError):
        await message.answer("Неверный формат команды. Используйте: /unverify <ID объекта>")


# --- Обработка заявок на бронирование ---

@router.callback_query(F.data.startswith("booking:confirm:"))
async def confirm_booking(callback: CallbackQuery, bot: Bot):
    """
    Обрабатывает нажатие на кнопку "Принять" заявку.
    """
    booking_id = int(callback.data.split(":")[2])
    
    await update_booking_status(booking_id, "confirmed")
    booking = await get_booking_with_details(booking_id)
    if not booking:
        await callback.answer("Бронирование не найдено.", show_alert=True)
        return

    await callback.message.edit_text(f"{callback.message.text}\n\n--- \n✅ ВЫ ПРИНЯЛИ ЭТУ ЗАЯВКУ ---")
    
    try:
        # Планируем отправку запроса на отзыв через 2 минуты
        run_date = datetime.now(ZoneInfo("Europe/Kaliningrad")) + timedelta(minutes=2)
        scheduler.add_job(
            request_review,
            'date',
            run_date=run_date,
            kwargs={
                "bot_token": settings.BOT_TOKEN.get_secret_value(),
                "chat_id": booking.user.telegram_id,
                "booking_id": booking.id,
                "property_title": booking.property.title
            }
        )
        logging.info(f"Запланирован запрос отзыва для бронирования {booking.id} на {run_date}")
    except Exception as e:
        logging.error(f"Ошибка при планировании запроса на отзыв: {e}")

    try:
        await bot.send_message(
            chat_id=booking.user.telegram_id,
            text=f"🎉 Ваша заявка на бронирование объекта «{booking.property.title}» была ОДОБРЕНА!\n\nВладелец скоро свяжется с вами для уточнения деталей."
        )
    except TelegramAPIError as e:
        logging.error(f"Telegram API Error при отправке уведомления арендатору: {e}")
        
    await callback.answer("Вы успешно приняли заявку!")


@router.callback_query(F.data.startswith("booking:reject:"))
async def reject_booking(callback: CallbackQuery, bot: Bot):
    """
    Обрабатывает нажатие на кнопку "Отклонить" заявку.
    """
    booking_id = int(callback.data.split(":")[2])
    
    await update_booking_status(booking_id, "rejected")
    booking = await get_booking_with_details(booking_id)
    if not booking:
        await callback.answer("Бронирование не найдено.", show_alert=True)
        return

    await callback.message.edit_text(f"{callback.message.text}\n\n--- \n❌ ВЫ ОТКЛОНИЛИ ЭТУ ЗАЯВКУ ---")

    try:
        await bot.send_message(
            chat_id=booking.user.telegram_id,
            text=f"😔 К сожалению, ваша заявка на бронирование объекта «{booking.property.title}» была ОТКЛОНЕНА."
        )
    except TelegramAPIError as e:
        logging.error(f"Telegram API Error при отправке уведомления арендатору: {e}")
        
    await callback.answer("Вы отклонили заявку.")