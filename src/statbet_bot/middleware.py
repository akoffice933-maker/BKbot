"""Middleware for error handling and rate limiting."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, Update, CallbackQuery
from statbet_bot.constants import BotDefaults

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Global error handler middleware."""
    
    def __init__(self):
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Any],
        event: Message | CallbackQuery | Update,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in handler: {e}", exc_info=True)
            if isinstance(event, Message):
                try:
                    await event.answer(
                        "⚠️ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
                    )
                except Exception:
                    logger.error("Failed to send error message to user", exc_info=True)
                return None
            raise


class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting middleware to prevent abuse."""
    
    def __init__(self, cooldown: timedelta = None):
        super().__init__()
        self.cooldown = cooldown or timedelta(seconds=BotDefaults.RATE_LIMIT_COOLDOWN_SECONDS)
        self.last_call: Dict[int, datetime] = {}
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Any],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = datetime.now()
        
        if user_id in self.last_call:
            time_since_last = now - self.last_call[user_id]
            if time_since_last < self.cooldown:
                remaining = (self.cooldown - time_since_last).seconds
                await event.answer(
                    f"⏳ Пожалуйста, подождите {remaining} сек. перед следующим запросом."
                )
                return
        
        self.last_call[user_id] = now
        
        cleanup_threshold = now - timedelta(minutes=1)
        self.last_call = {
            uid: ts for uid, ts in self.last_call.items()
            if ts > cleanup_threshold
        }
        
        return await handler(event, data)
