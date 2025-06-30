from datetime import date
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload

from src.models.models import Property, PriceRule
from .db import async_session_maker

async def get_price_for_date(session, property_id: int, target_date: date, base_price: int) -> int:
    """
    Определяет цену для конкретной даты, учитывая правила.
    Правило, которое начинается позже, имеет приоритет.
    """
    query = (
        select(PriceRule.price)
        .where(
            and_(
                PriceRule.property_id == property_id,
                PriceRule.start_date <= target_date,
                PriceRule.end_date >= target_date
            )
        )
        .order_by(PriceRule.start_date.desc())
        .limit(1)
    )
    result = await session.execute(query)
    rule_price = result.scalar_one_or_none()

    return rule_price if rule_price is not None else base_price

async def get_property_with_price_rules(session, property_id: int):
    """Загружает объект со всеми его ценовыми правилами."""
    query = (
        select(Property)
        .where(Property.id == property_id)
        .options(selectinload(Property.price_rules))
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def add_price_rule(property_id: int, start_date: date, end_date: date, price: int) -> PriceRule:
    """Создает новое ценовое правило."""
    async with async_session_maker() as session:
        new_rule = PriceRule(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            price=price
        )
        session.add(new_rule)
        await session.commit()
        await session.refresh(new_rule)
        return new_rule

async def get_price_rules_for_property(property_id: int) -> list[PriceRule]:
    """Получает все ценовые правила для объекта."""
    async with async_session_maker() as session:
        query = select(PriceRule).where(PriceRule.property_id == property_id).order_by(PriceRule.start_date)
        result = await session.execute(query)
        return result.scalars().all()

async def delete_price_rule(rule_id: int) -> bool:
    """Удаляет ценовое правило по его ID."""
    async with async_session_maker() as session:
        result = await session.execute(delete(PriceRule).where(PriceRule.id == rule_id))
        await session.commit()
        return result.rowcount > 0
