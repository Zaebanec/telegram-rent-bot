from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.utils.states import LeaveReview
from app.services.review_service import add_review, get_latest_reviews
from app.keyboards.inline_keyboards import get_rating_keyboard

router = Router()

# ... (код process_rating и process_comment без изменений) ...
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


# --- НОВЫЙ ОБРАБОТЧИК ---
@router.callback_query(F.data.startswith("view_reviews:"))
async def view_reviews_handler(callback: CallbackQuery):
    property_id = int(callback.data.split(":")[1])
    reviews = await get_latest_reviews(property_id)
    
    if not reviews:
        await callback.answer("У этого объекта еще нет отзывов.", show_alert=True)
        return

    response_text = "<b>Последние отзывы:</b>\n\n"
    for review in reviews:
        stars = "⭐️" * review.rating
        comment = f" — «{review.text}»" if review.text else ""
        response_text += f"{stars}{comment}\n--------------------\n"
        
    await callback.message.answer(response_text)
    await callback.answer()