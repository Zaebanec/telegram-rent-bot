import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем сервисы, которые будем тестировать и которые нужны для подготовки данных
from src.services.user_service import add_user
from src.services.property_service import (
    add_property, 
    get_all_properties, 
    get_properties_by_owner,
    toggle_property_activity,
    delete_property
)

pytestmark = pytest.mark.asyncio


async def test_add_and_get_property(db_session: AsyncSession):
    """
    Тест: проверяем успешное добавление объекта и его получение из БД.
    """
    # 1. Подготовка: создаем тестового пользователя-владельца
    owner = await add_user(telegram_id=111, username="owner1", first_name="Owner")

    # 2. Подготовка: данные для нового объекта
    property_data = {
        "title": "Тестовый Лофт",
        "description": "Отличное место для отдыха",
        "district": "Центральный",
        "address": "ул. Тестовая, 1",
        "rooms": "2",
        "price_per_night": "5000",
        "max_guests": "4",
        "property_type": "Квартира"
    }

    # 3. Выполнение: добавляем объект в БД
    property_id = await add_property(property_data, owner_id=owner.telegram_id)

    # 4. Проверка: получаем все объекты и убеждаемся, что наш объект там есть
    all_properties = await get_all_properties(districts=["Центральный"])
    
    assert len(all_properties) == 1
    new_property = all_properties[0]
    assert new_property.id == property_id
    assert new_property.title == "Тестовый Лофт"
    assert new_property.owner_id == owner.telegram_id
    # Проверяем, что строковые значения корректно преобразовались в числовые
    assert new_property.rooms == 2
    assert new_property.price_per_night == 5000
    assert new_property.max_guests == 4


async def test_toggle_property_activity(db_session: AsyncSession):
    """
    Тест: проверяем активацию и деактивацию объекта.
    """
    # 1. Подготовка: создаем владельца и его объект
    owner = await add_user(telegram_id=222, username="owner2", first_name="Owner")
    property_data = {"title": "Активный объект", "district": "Тест", "address": "a", "rooms": "1", "price_per_night": "1000", "max_guests": "1", "property_type": "Апартаменты"}
    property_id = await add_property(property_data, owner_id=owner.telegram_id)

    # 2. Выполнение и Проверка:
    # Изначально объект активен (is_active=True по умолчанию)
    props_before = await get_properties_by_owner(owner.telegram_id)
    assert props_before[0].is_active is True

    # Деактивируем объект
    await toggle_property_activity(property_id)
    props_after_toggle = await get_properties_by_owner(owner.telegram_id)
    assert props_after_toggle[0].is_active is False

    # Снова активируем
    await toggle_property_activity(property_id)
    props_after_second_toggle = await get_properties_by_owner(owner.telegram_id)
    assert props_after_second_toggle[0].is_active is True


async def test_delete_property(db_session: AsyncSession):
    """
    Тест: проверяем удаление объекта.
    """
    # 1. Подготовка: создаем владельца и его объект
    owner = await add_user(telegram_id=333, username="owner3", first_name="Owner")
    property_data = {"title": "Объект на удаление", "district": "Тест", "address": "a", "rooms": "1", "price_per_night": "1000", "max_guests": "1", "property_type": "Дом"}
    property_id = await add_property(property_data, owner_id=owner.telegram_id)

    # 2. Проверка до удаления
    props_before = await get_properties_by_owner(owner.telegram_id)
    assert len(props_before) == 1

    # 3. Выполнение: удаляем объект
    await delete_property(property_id)

    # 4. Проверка после удаления
    props_after = await get_properties_by_owner(owner.telegram_id)
    assert len(props_after) == 0