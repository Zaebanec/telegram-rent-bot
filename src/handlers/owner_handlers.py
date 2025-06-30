from aiogram import Router
from .owner import add_property, manage_property, edit_property

owner_router = Router()

owner_router.include_router(add_property.router)
owner_router.include_router(manage_property.router)
owner_router.include_router(edit_property.router)