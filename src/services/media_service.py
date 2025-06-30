from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.models import PropertyMedia
from .db import async_session_maker

async def add_photos_to_property(property_id: int, photo_file_ids: list[str]):
    async with async_session_maker() as session:
        for file_id in photo_file_ids:
            new_photo = PropertyMedia(
                property_id=property_id,
                file_id=file_id,
                media_type='photo'
            )
            session.add(new_photo)
        await session.commit()
        
async def add_video_note_to_property(property_id: int, file_id: str):
    async with async_session_maker() as session:
        new_video_note = PropertyMedia(
            property_id=property_id,
            file_id=file_id,
            media_type='video_note'
        )
        session.add(new_video_note)
        await session.commit()

async def delete_all_media_for_property(property_id: int):
    async with async_session_maker() as session:
        await session.execute(delete(PropertyMedia).where(PropertyMedia.property_id == property_id))
        await session.commit()

async def delete_one_media_item(media_id: int):
    async with async_session_maker() as session:
        await session.execute(delete(PropertyMedia).where(PropertyMedia.id == media_id))
        await session.commit()