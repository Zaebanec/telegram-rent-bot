from aiogram import Router
# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Убираем webapp ---
from .user import common, search, booking, review 

user_router = Router()

# Регистрируем все роутеры, КРОМЕ webapp
user_router.include_router(common.router)
user_router.include_router(search.router)
user_router.include_router(booking.router)
user_router.include_router(review.router)