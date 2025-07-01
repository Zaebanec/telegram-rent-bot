from datetime import date
from typing import List
from sqlalchemy import select, delete, and_
from sqlalchemy.dialects.postgresql import insert

from src.models.models import UnavailableDate
from src.services.db import async_session_maker

async def get_manual_blocks(property_id: int) -> List[UnavailableDate]:
    """Возвращает список дат, заблокированных владельцем вручную."""
    async with async_session_maker() as session:
        query = select(UnavailableDate).where(UnavailableDate.property_id == property_id)
        result = await session.execute(query)
        return result.scalars().all()

async def set_availability_for_period(property_id: int, dates: List[date], is_available: bool, comment: str | None):
    """
    Устанавливает статус доступности для списка дат.
    Если is_available=False, добавляет/обновляет блокировки.
    Если is_available=True, удаляет блокировки.
    """
    async with async_session_maker() as session:
        if not is_available:
            # Используем "ON CONFLICT DO UPDATE", чтобы обновить комментарий, если дата уже заблокирована
            stmt = insert(UnavailableDate).values(
                [
                    {"property_id": property_id, "date": d, "comment": comment}
                    for d in dates
                ]
            )
            update_stmt = stmt.on_conflict_do_update(
                index_elements=['property_id', 'date'], # Уникальный ключ
                set_={'comment': stmt.excluded.comment}
            )
            await session.execute(update_stmt)
        else:
            # Удаляем все блокировки для указанных дат
            stmt = delete(UnavailableDate).where(
                and_(
                    UnavailableDate.property_id == property_id,
                    UnavailableDate.date.in_(dates)
                )
            )
            await session.execute(stmt)
        
        await session.commit()