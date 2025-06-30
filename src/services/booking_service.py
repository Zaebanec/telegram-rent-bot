from datetime import datetime, timedelta
from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import selectinload

from src.models.models import Booking, Property
from .db import async_session_maker


async def create_booking(user_id: int, property_id: int, start_date: datetime, end_date: datetime) -> Booking:
    """Создает новую заявку на бронирование с датами и статусом 'pending'."""
    async with async_session_maker() as session:
        new_booking = Booking(
            user_id=user_id,
            property_id=property_id,
            start_date=start_date,
            end_date=end_date
        )
        session.add(new_booking)
        await session.commit()
        return new_booking

async def update_booking_status(booking_id: int, status: str) -> Booking | None:
    """Обновляет статус бронирования (pending, confirmed, rejected)."""
    async with async_session_maker() as session:
        booking = await session.get(Booking, booking_id)
        if booking:
            booking.status = status
            await session.commit()
        return booking

async def get_booking_with_details(booking_id: int):
    """Получает бронирование со связанными данными пользователя и объекта."""
    async with async_session_maker() as session:
        query = (
            select(Booking)
            .where(Booking.id == booking_id)
            .options(selectinload(Booking.user), selectinload(Booking.property))
        )
        result = await session.execute(query)
        return result.unique().scalar_one_or_none()


async def count_pending_bookings_for_owner(owner_id: int) -> int:
    """Подсчитывает количество необработанных заявок ('pending') для владельца."""
    async with async_session_maker() as session:
        query = (
            select(func.count(Booking.id))
            .join(Property, Booking.property_id == Property.id)
            .where(
                and_(
                    Property.owner_id == owner_id,
                    Booking.status == 'pending'
                )
            )
        )
        result = await session.execute(query)
        return result.scalar_one()

async def get_booked_dates_for_property(property_id: int) -> list[datetime.date]:
    """
    Возвращает список всех дат, занятых подтвержденными бронированиями ('confirmed').
    """
    async with async_session_maker() as session:
        query = select(Booking.start_date, Booking.end_date).where(
            and_(
                Booking.property_id == property_id,
                Booking.status == 'confirmed'
            )
        )
        result = await session.execute(query)
        booked_dates = []
        for start_date, end_date in result.all():
            current_date = start_date
            # Бронирование не включает день выезда, поэтому <
            while current_date < end_date:
                booked_dates.append(current_date.date())
                current_date += timedelta(days=1)
        return booked_dates
