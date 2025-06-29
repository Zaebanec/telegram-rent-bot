from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.utils.states import LeaveReview
from app.services.review_service import add_review, get_latest_reviews
from app.keyboards.inline_keyboards import get_rating_keyboard

router = Router()

# --- Обработчики для оставления отзыва (остаются без изменений) ---
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


# --- Обработчик для просмотра отзывов ---
@router.callback_query(F.data.startswith("view_reviews:"))
async def view_reviews_handler(callback: CallbackQuery):
    """
    Обработчик для кнопки 'Читать отзывы'.
    Получает и форматирует последние отзывы для объекта.
    """
    await callback.answer()
    property_id = int(callback.data.split(":")[1])
    
    # Получаем последние 5 отзывов из сервисного слоя
    reviews = await get_latest_reviews(property_id, limit=5)
    
    if not reviews:
        await callback.message.answer("У этого объекта еще нет отзывов.")
        return

    # Форматируем отзывы в одно красивое сообщение
    response_text = "<b>Последние отзывы:</b>\n\n"
    for review in reviews:
        stars = "⭐️" * review.rating
        # Добавляем текст отзыва, если он есть
        comment = f" — «{review.text}»" if review.text else ""
        response_text += f"{stars}{comment}\n"
        # Добавляем разделитель
        response_text += "--------------------\n"
        
    await callback.message.answer(response_text)