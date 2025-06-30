import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class ErrorCatcherMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            # Пытаемся выполнить основной обработчик
            return await handler(event, data)
        except Exception as e:
            # Если произошла любая ошибка, логируем ее
            logging.exception("Критическая ошибка в обработчике: %s", e)
            # Мы не пробрасываем ошибку дальше, чтобы aiohttp
            # не вернул Telegram'у ошибку 500.
            # Это "проглатывает" ошибку и позволяет боту работать дальше.