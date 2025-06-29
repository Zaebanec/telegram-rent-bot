from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.models import Booking, Review
from .db import async_session_maker

async def add_review(booking_id: int, rating: int, text: str | None):
    async with async_session_maker() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            return

        new_review = Review(
            property_id=booking.property_id,
            user_id=booking.user_id,
            booking_id=booking_id,
            rating=rating,
            text=text
        )
        session.add(new_review)
        await session.commit()

# --- НОВЫЕ ФУНКЦИИ ---

async def get_reviews_summary(property_id: int) -> tuple[float | None, int]:
    """
    Возвращает средний рейтинг и количество отзывов для объекта.
    """
    async with async_session_maker() as session:
        query = (
            select(
                func.avg(Review.rating),
                func.count(Review.id)
            )
            .where(Review.property_id == property_id)
        )
        result = await session.execute(query)
        # one_or_none() вернет (None, 0), если отзывов нет
        avg_rating, count = result.one_or_none() or (None, 0)
        return avg_rating, count

async def get_latest_reviews(property_id: int, limit: int = 5):
    """
    Возвращает последние N отзывов для объекта.
    """
    async with async_session_maker() as session:
        query = (
            select(Review)
            .where(Review.property_id == property_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return result.scalars().all()