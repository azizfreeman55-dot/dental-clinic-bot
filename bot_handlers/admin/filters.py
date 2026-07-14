from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from database.pool import get_pool
from database.queries.admin import is_admin as db_is_admin


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        pool = get_pool()
        return await db_is_admin(pool, event.from_user.id)
