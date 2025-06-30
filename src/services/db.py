from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.core.settings import settings

# echo=False, чтобы не засорять логи SQL-запросами в продакшене
engine = create_async_engine(settings.DATABASE_URL_asyncpg, echo=False) 
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)