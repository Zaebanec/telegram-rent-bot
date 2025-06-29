from aiogram import Router

# Импортируем наши большие "агрегаторы"
from .user_handlers import user_router
from .owner_handlers import owner_router
from .admin_handlers import router as admin_router
# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Импортируем webapp_router напрямую ---
from .user.webapp import router as webapp_router

# Создаем главный роутер всего приложения
main_router = Router()

# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Регистрируем webapp_router САМЫМ ПЕРВЫМ ---
# Это дает ему наивысший приоритет.
main_router.include_router(webapp_router)

# Далее регистрируем остальные роутеры.
# Порядок важен: админские команды должны проверяться до общих.
main_router.include_router(admin_router)
main_router.include_router(owner_router)
main_router.include_router(user_router)