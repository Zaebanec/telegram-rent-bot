import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user_service import add_user
from src.services.property_service import add_property
from src.services.booking_service import (
    create_booking, 
    update_booking_status, 
    get_booked_dates_for_property,
    count_pending_bookings_for_owner
)

pytestmark = pytest.mark.asyncio


# Мы УДАЛИЛИ фикстуру setup_for_booking


async def test_create_and_count_pending_booking(db_session: AsyncSession):
    """
    Тест: проверяем создание бронирования и счетчик ожидающих заявок.
    """
    # --- ИЗМЕНЕНИЕ: Вся подготовка данных теперь внутри теста ---
    owner = await add_user(telegram_id=1001, username="booking_owner_1", first_name="Owner")
    client = await add_user(telegram_id=2002, username="booking_client_1", first_name="Client")
    property_data = {"title": "Объект 1", "district": "Бронь", "address": "a", "rooms": "1", "price_per_night": "1000", "max_guests": "1", "property_type": "Квартира"}
    property_id = await add_property(property_data, owner_id=owner.telegram_id)
    
    # 1. Проверка до создания
    pending_count_before = await count_pending_bookings_for_owner(owner.telegram_id)
    assert pending_count_before == 0

    # 2. Выполнение: создаем бронирование
    start_date = datetime(2025, 10, 1)
    end_date = datetime(2025, 10, 5)
    new_booking = await create_booking(
        user_id=client.telegram_id,
        property_id=property_id,
        start_date=start_date,
        end_date=end_date
    )

    # 3. Проверка после создания
    assert new_booking is not None
    assert new_booking.status == 'pending'
    
    pending_count_after = await count_pending_bookings_for_owner(owner.telegram_id)
    assert pending_count_after == 1


async def test_update_booking_status_and_dates(db_session: AsyncSession):
    """
    Тест: проверяем обновление статуса брони и получение списка занятых дат.
    """
    # --- ИЗМЕНЕНИЕ: Вся подготовка данных теперь внутри теста ---
    owner = await add_user(telegram_id=3003, username="booking_owner_2", first_name="Owner")
    client = await add_user(telegram_id=4004, username="booking_client_2", first_name="Client")
    property_data = {"title": "Объект 2", "district": "Бронь", "address": "b", "rooms": "2", "price_per_night": "2000", "max_guests": "2", "property_type": "Дом"}
    property_id = await add_property(property_data, owner_id=owner.telegram_id)

    start_date = datetime(2025, 11, 10)
    end_date = datetime(2025, 11, 12) # 2 ночи: 10 и 11
    booking = await create_booking(client.telegram_id, property_id, start_date, end_date)

    # 1. Проверка до обновления
    booked_dates_before = await get_booked_dates_for_property(property_id)
    assert len(booked_dates_before) == 0

    # 2. Выполнение: подтверждаем бронь
    await update_booking_status(booking.id, "confirmed")

    # 3. Проверка после обновления
    booked_dates_after = await get_booked_dates_for_property(property_id)
    assert len(booked_dates_after) == 2
    assert start_date.date() in booked_dates_after
    assert (start_date.date() + timedelta(days=1)) in booked_dates_after
    assert end_date.date() not in booked_dates_after