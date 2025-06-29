from aiogram import Router
from .user import common, search, booking, review, webapp # <-- Добавляем webapp

user_router = Router()

# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Регистрируем webapp ПЕРВЫМ ---
# Это гарантирует, что фильтр F.web_app_data проверится до любых других
user_router.include_router(webapp.router) 

user_router.include_router(common.router)
user_router.include_router(search.router)
user_router.include_router(booking.router)
user_router.include_router(review.router)