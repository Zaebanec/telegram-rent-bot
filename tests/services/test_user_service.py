import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.user_service import add_user, get_user

pytestmark = pytest.mark.asyncio

async def test_add_and_get_user(db_session: AsyncSession):
    test_user_id = 123
    created_user = await add_user(test_user_id, "test", "Test")
    retrieved_user = await get_user(test_user_id)
    assert retrieved_user is not None
    assert retrieved_user.telegram_id == test_user_id

async def test_add_existing_user(db_session: AsyncSession):
    test_user_id = 456
    await add_user(test_user_id, "existing", "First")
    # В нашей реализации add_user не обновляет данные, а просто возвращает существующего
    # Это нормально, но тест должен это проверять
    user_again = await add_user(test_user_id, "new_username", "NewName")
    assert user_again.first_name == "First"