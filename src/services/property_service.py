from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from src.models.models import Property, PropertyMedia
from .db import async_session_maker


async def add_property(data: dict, owner_id: int) -> int:
    async with async_session_maker() as session:
        rooms_str = data.get('rooms', '0')
        rooms_int = 0 if rooms_str == 'Студия' else int(rooms_str.replace('+', ''))
        guests_str = data.get('max_guests', '1')
        guests_int = int(guests_str.replace('+', ''))
        new_property = Property(
            owner_id=owner_id,
            title=data.get('title'),
            description=data.get('description'),
            district=data.get('district'),
            address=data.get('address'),
            rooms=rooms_int,
            price_per_night=int(data.get('price_per_night')),
            max_guests=guests_int,
            property_type=data.get('property_type')
        )
        session.add(new_property)
        await session.flush()
        property_id = new_property.id
        await session.commit()
        return property_id

async def get_all_properties(
    districts: list[str] | None = None, 
    max_price: int | None = None, 
    min_guests: int | None = None
):
    """
    Возвращает список всех активных объектов с учетом фильтров.
    """
    async with async_session_maker() as session:
        query = (
            select(Property)
            .where(Property.is_active == True)
            .options(selectinload(Property.media))
        )
        
        if districts:
            query = query.where(Property.district.in_(districts)) # Используем .in_ для списка
        if max_price:
            query = query.where(Property.price_per_night <= max_price)
        if min_guests:
            query = query.where(Property.max_guests >= min_guests)
            
        result = await session.execute(query)
        return result.unique().scalars().all()
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---

async def get_property_with_media_and_owner(property_id: int):
    async with async_session_maker() as session:
        query = (
            select(Property)
            .where(Property.id == property_id)
            .options(selectinload(Property.owner), selectinload(Property.media))
        )
        result = await session.execute(query)
        prop = result.unique().scalar_one_or_none()
        if prop:
            photo_files = [media.file_id for media in prop.media if media.media_type == 'photo']
            video_file = next((media.file_id for media in prop.media if media.media_type == 'video_note'), None)
            return prop, photo_files, video_file
        return None, [], None

async def set_property_verified(property_id: int, status: bool = True):
    async with async_session_maker() as session:
        query = update(Property).where(Property.id == property_id).values(is_verified=status)
        await session.execute(query)
        await session.commit()

async def get_properties_by_owner(owner_id: int):
    async with async_session_maker() as session:
        query = select(Property).where(Property.owner_id == owner_id).order_by(Property.id)
        result = await session.execute(query)
        return result.scalars().all()

async def toggle_property_activity(property_id: int) -> bool:
    async with async_session_maker() as session:
        prop = await session.get(Property, property_id)
        if prop:
            prop.is_active = not prop.is_active
            await session.commit()
            return prop.is_active
    return False

async def delete_property(property_id: int):
    async with async_session_maker() as session:
        await session.execute(delete(Property).where(Property.id == property_id))
        await session.commit()

async def update_property_field(property_id: int, field: str, value):
    async with async_session_maker() as session:
        query = update(Property).where(Property.id == property_id).values({field: value})
        await session.execute(query)
        await session.commit()

# --- НОВАЯ ФУНКЦИЯ ---
async def get_owner_properties_summary(owner_id: int) -> tuple[int, int]:
    """
    Подсчитывает общее и активное количество объектов владельца.
    Возвращает кортеж (total_count, active_count).
    """
    async with async_session_maker() as session:
        # Считаем общее количество
        total_query = select(func.count(Property.id)).where(Property.owner_id == owner_id)
        total_result = await session.execute(total_query)
        total_count = total_result.scalar_one()

        # Считаем количество активных
        active_query = select(func.count(Property.id)).where(
            and_(Property.owner_id == owner_id, Property.is_active == True)
        )
        active_result = await session.execute(active_query)
        active_count = active_result.scalar_one()
        
        return total_count, active_count