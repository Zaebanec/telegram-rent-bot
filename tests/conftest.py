import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.core.settings import settings
from src.models.base import Base
from src.services.db import async_session_maker as main_async_session_maker

# Создаем отдельный движок и сессию для тестовой БД
test_engine = create_async_engine(settings.DATABASE_URL_asyncpg)
test_async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """
    Создает экземпляр цикла событий для всех тестов.
    Эта реализация вызывает DeprecationWarning, но она РАБОТАЕТ.
    Мы вернемся к исправлению предупреждения позже, отдельной задачей.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Фикстура для создания и удаления таблиц в тестовой БД.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session():
    """
    Фикстура, которая предоставляет сессию БД для каждого теста.
    """
    main_async_session_maker.kw['bind'] = test_engine
    
    async with test_async_session_maker() as session:
        await session.begin_nested()
        yield session
        await session.rollback()