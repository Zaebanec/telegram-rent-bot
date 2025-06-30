from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.models import User
from .db import async_session_maker

async def add_user(telegram_id: int, username: str | None, first_name: str) -> User:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            new_user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            session.add(new_user)
            await session.commit()
            return new_user
        return user

async def get_user(user_id: int) -> User | None:
    async with async_session_maker() as session:
        return await session.get(User, user_id)

async def set_user_role(user_id: int, role: str):
    async with async_session_maker() as session:
        query = update(User).where(User.telegram_id == user_id).values(role=role)
        await session.execute(query)
        await session.commit()