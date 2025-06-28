from aiogram import Router
from .user import common, search, booking, review

user_router = Router()

user_router.include_router(common.router)
user_router.include_router(search.router)
user_router.include_router(booking.router)
user_router.include_router(review.router)