from aiogram import Router

# Импортируем наши большие "агрегаторы"
from .user_handlers import user_router
from .owner_handlers import owner_router
from .admin_handlers import router as admin_router
from .user.webapp import router as webapp_router
# --- НОВЫЙ ИМПОРТ ---
from .common_handlers import router as common_router

# Создаем главный роутер всего приложения
main_router = Router()

# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Регистрируем универсальные обработчики ПЕРВЫМИ ---
main_router.include_router(common_router)
main_router.include_router(webapp_router)

# Далее регистрируем остальные роутеры.
main_router.include_router(admin_router)
main_router.include_router(owner_router)
main_router.include_router(user_router)