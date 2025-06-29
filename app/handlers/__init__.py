from aiogram import Router

# Импортируем только три наших больших "агрегатора"
from .user_handlers import user_router
from .owner_handlers import owner_router
from .admin_handlers import router as admin_router

# Создаем главный роутер всего приложения
main_router = Router()

# Регистрируем в нем наши большие агрегаторы.
# Порядок важен: сначала админ, потом владелец, потом обычный пользователь.
main_router.include_router(admin_router)
main_router.include_router(owner_router)
main_router.include_router(user_router)