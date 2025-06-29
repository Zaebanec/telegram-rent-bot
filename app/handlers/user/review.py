from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.utils.states import LeaveReview
from app.services.review_service import add_review, get_latest_reviews, get_reviews_summary
# --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Импортируем нужные сервисы и клавиатуры ---
from app.services.property_service import get_property_with_media_and_owner
from app.keyboards.inline_keyboards import get_rating_keyboard, get_property_card_keyboard

router = Router()

# Обработчики для оставления отзыва (без изменений)
# ... (код process_rating и process_comment)
@router.callback_query(F.data.startswith("review:"))
async def process_rating(callback: CallbackQuery, state: FSMContext):
    _, booking_id_str, _, rating_str = callback.data.split(":")
    await state.update_data(
        booking_id=int(booking_id_str),
        rating=int(rating_str)
    )
    await callback.message.edit_text(
        f"Вы поставили оценку: {'⭐️' * int(rating_str)}\n\n"
        "Теперь, пожалуйста, напишите текстовый комментарий... "
        "Или отправьте '-', если не хотите оставлять комментарий."
    )
    await state.set_state(LeaveReview.waiting_for_comment)
    await callback.answer()

@router.message(LeaveReview.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    booking_id = data.get('booking_id')
    rating = data.get('rating')
    comment_text = message.text if message.text != '-' else None
    await add_review(
        booking_id=booking_id,
        rating=rating,
        text=comment_text
    )
    await message.answer("Спасибо! Ваш отзыв был успешно сохранен.")
    await state.clear()


@router.callback_query(F.data.startswith("view_reviews:"))
async def view_reviews_handler(callback: CallbackQuery):
    """
    Обработчик для кнопки 'Читать отзывы'.
    Получает отзывы, форматирует их и ВОЗВРАЩАЕТ МЕНЮ.
    """
    await callback.answer()
    property_id = int(callback.data.split(":")[1])
    
    reviews = await get_latest_reviews(property_id, limit=5)
    
    if not reviews:
        await callback.message.answer("У этого объекта еще нет отзывов.")
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Даже если отзывов нет, вернем меню ---
    else:
        response_text = "<b>Последние отзывы:</b>\n\n"
        for review in reviews:
            stars = "⭐️" * review.rating
            comment = f" — «{review.text}»" if review.text else ""
            response_text += f"{stars}{comment}\n"
            response_text += "--------------------\n"
        await callback.message.answer(response_text)

    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Возвращаем меню в любом случае ---
    prop, photo_files, video_file = await get_property_with_media_and_owner(property_id)
    _, reviews_count = await get_reviews_summary(prop.id)

    await callback.message.answer(
        text="Выберите дальнейшее действие:",
        reply_markup=get_property_card_keyboard(
            property_id=prop.id,
            photos_count=len(photo_files),
            has_video=bool(video_file),
            reviews_count=reviews_count
        )
    )