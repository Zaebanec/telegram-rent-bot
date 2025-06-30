from datetime import date
from sqlalchemy import select, delete, and_
from src.models.models import UnavailableDate
from .db import async_session_maker

async def get_manual_blocks(property_id: int) -> list[UnavailableDate]:
    """Возвращает список объектов UnavailableDate, заблокированных владельцем вручную."""
    async with async_session_maker() as session:
        query = select(UnavailableDate).where(UnavailableDate.property_id == property_id)
        result = await session.execute(query)
        return result.scalars().all()

async def toggle_manual_availability(property_id: int, target_date: date, comment: str | None = None) -> str:
    """
    Переключает статус ручной блокировки для даты.
    Если дата блокируется, можно передать комментарий.
    """
    async with async_session_maker() as session:
        query = select(UnavailableDate).where(
            and_(
                UnavailableDate.property_id == property_id,
                UnavailableDate.date == target_date
            )
        )
        result = await session.execute(query)
        existing_block = result.scalar_one_or_none()

        if existing_block:
            await session.delete(existing_block)
            new_status = 'available'
        else:
            new_block = UnavailableDate(property_id=property_id, date=target_date, comment=comment)
            session.add(new_block)
            new_status = 'manual_block'
        
        await session.commit()
        return new_status
