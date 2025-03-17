from typing import Any, Awaitable, Callable, Dict, Union
from aiogram.types import Message, CallbackQuery
from database.database import get_db

class DatabaseMiddleware:
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        db = next(get_db())
        data["db"] = db
        try:
            return await handler(event, data)
        finally:
            db.close() 