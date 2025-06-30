from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from src.core.settings import settings

# Добавляем /help в список для всех пользователей
user_commands = [
    BotCommand(command="start", description="🚀 Перезапустить бота / Главное меню"),
    BotCommand(command="help", description="ℹ️ Справка по боту"),
    BotCommand(command="cancel", description="❌ Отменить текущее действие")
]

# Администраторы автоматически получат эту команду
admin_commands = user_commands + [
    BotCommand(command="myproperties", description="📋 Мои объекты"),
    BotCommand(command="addproperty", description="🏠 Добавить новый объект"),
    BotCommand(command="verify", description="✅ Верифицировать объект"),
    BotCommand(command="unverify", description="❌ Снять верификацию"),
    BotCommand(command="setrole", description="👤 Назначить роль")
]


async def set_commands(bot: Bot):
    await bot.set_my_commands(commands=user_commands, scope=BotCommandScopeDefault())
    
    # Убедимся, что у админов будет полный список
    for admin_id in settings.ADMIN_IDS:
        await bot.set_my_commands(commands=admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))