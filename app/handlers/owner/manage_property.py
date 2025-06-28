from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

# Обновляем импорты
from app.services.property_service import (get_properties_by_owner, toggle_property_activity, 
                                         delete_property, get_property_with_media_and_owner,
                                         get_owner_properties_summary)
from app.services.booking_service import count_pending_bookings_for_owner
from app.keyboards.inline_keyboards import (get_property_management_keyboard, 
                                           get_delete_confirmation_keyboard)

router = Router()

def format_my_property_card(prop) -> str:
    status_verified = "✅ Верифицирован" if prop.is_verified else "☑️ Не верифицирован"
    status_active = "🟢 Активен" if prop.is_active else "🔴 Скрыт"
    return (
        f"🆔 `{prop.id}`: **{prop.title}**\n"
        f"Статусы: {status_verified}, {status_active}"
    )

# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Добавляем сводку ---
@router.message(Command("myproperties"))
async def my_properties_list(message: Message):
    owner_id = message.from_user.id
    
    # Получаем сводную информацию
    total_props, active_props = await get_owner_properties_summary(owner_id)
    pending_bookings = await count_pending_bookings_for_owner(owner_id)
    
    # Отправляем сводное сообщение
    summary_text = (
        f"Здравствуйте, {message.from_user.first_name}!\n\n"
        f"<b>Ваша приборная панель:</b>\n"
        f"Всего объектов: {total_props}\n"
        f"Активных в поиске: {active_props}\n"
        f"Новых заявок на бронь: {pending_bookings}"
    )
    await message.answer(summary_text)

    # Получаем и выводим список объектов, как и раньше
    properties = await get_properties_by_owner(owner_id=owner_id)
    if not properties:
        await message.answer("У вас пока нет добавленных объектов. Используйте /addproperty, чтобы добавить первый.")
        return
    
    await message.answer("<b>Ваши объекты:</b>")
    for prop in properties:
        await message.answer(
            format_my_property_card(prop),
            reply_markup=get_property_management_keyboard(prop.id, prop.is_active)
        )
# --- КОНЕЦ ИЗМЕНЕНИЯ ---


@router.callback_query(F.data.startswith("manage:toggle:"))
async def toggle_property_handler(callback: CallbackQuery):
    property_id = int(callback.data.split(":")[2])
    new_status = await toggle_property_activity(property_id)
    
    prop, _, _ = await get_property_with_media_and_owner(property_id)
    if prop:
        await callback.message.edit_text(
            format_my_property_card(prop),
            reply_markup=get_property_management_keyboard(prop.id, new_status)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("manage:delete:"))
async def delete_property_handler(callback: CallbackQuery):
    property_id = int(callback.data.split(":")[2])
    await callback.message.edit_reply_markup(
        reply_markup=get_delete_confirmation_keyboard(property_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("manage:delete_confirm:"))
async def delete_confirm_handler(callback: CallbackQuery):
    property_id = int(callback.data.split(":")[2])
    await delete_property(property_id)
    await callback.message.edit_text(f"Объект с ID `{property_id}` был успешно удален.")
    await callback.answer("Объект удален.", show_alert=True)

@router.callback_query(F.data == "manage:delete_cancel")
async def delete_cancel_handler(callback: CallbackQuery):
    # Вместо удаления разметки, вернем карточку объекта
    # Из-за вложенности, нам нужно найти ID объекта в кнопке
    prop_id = None
    for row in callback.message.reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data.startswith("manage:edit:"):
                prop_id = int(button.callback_data.split(":")[-1])
                break
        if prop_id:
            break

    if prop_id:
        prop, _, _ = await get_property_with_media_and_owner(prop_id)
        if prop:
            await callback.message.edit_text(
                format_my_property_card(prop),
                reply_markup=get_property_management_keyboard(prop.id, prop.is_active)
            )
    else:
        await callback.message.edit_text("Действие отменено.")
    await callback.answer("Удаление отменено.")