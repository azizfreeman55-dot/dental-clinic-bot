from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from database.pool import get_pool
from database.queries.admin import is_owner, add_admin, list_admins, remove_admin
from bot_handlers.admin.filters import IsAdmin

router = Router(name="manage_admins")
router.message.filter(IsAdmin())


@router.message(Command("admins"))
async def cmd_list_admins(message: Message):
    pool = get_pool()
    admins = await list_admins(pool)

    lines = ["👥 Список админов:\n"]
    for a in admins:
        role_label = "владелец" if a["role"] == "owner" else "менеджер"
        lines.append(f"• {a['full_name'] or 'без имени'} — {a['telegram_id']} ({role_label})")

    await message.answer("\n".join(lines))


@router.message(Command("addadmin"))
async def cmd_add_admin(message: Message, command: CommandObject):
    pool = get_pool()

    if not await is_owner(pool, message.from_user.id):
        await message.answer("Добавлять админов может только владелец.")
        return

    if not command.args:
        await message.answer(
            "Использование: <code>/addadmin telegram_id Имя</code>\n\n"
            "telegram_id нового админа можно узнать через @userinfobot — "
            "попросите его написать этому боту и прислать вам скриншот."
        )
        return

    parts = command.args.split(maxsplit=1)
    telegram_id_str = parts[0]
    full_name = parts[1] if len(parts) > 1 else "Admin"

    if not telegram_id_str.isdigit():
        await message.answer("telegram_id должен быть числом. Пример: /addadmin 123456789 Иван")
        return

    telegram_id = int(telegram_id_str)
    added = await add_admin(pool, telegram_id, full_name, role="manager")

    if added:
        await message.answer(f"✅ {full_name} ({telegram_id}) добавлен как админ.")
    else:
        await message.answer("Этот пользователь уже есть в списке админов.")


@router.message(Command("removeadmin"))
async def cmd_remove_admin(message: Message, command: CommandObject):
    pool = get_pool()

    if not await is_owner(pool, message.from_user.id):
        await message.answer("Удалять админов может только владелец.")
        return

    if not command.args or not command.args.strip().isdigit():
        await message.answer("Использование: /removeadmin telegram_id")
        return

    telegram_id = int(command.args.strip())
    removed = await remove_admin(pool, telegram_id)

    if removed:
        await message.answer(f"Админ {telegram_id} удалён.")
    else:
        await message.answer("Такого админа нет, либо это владелец (владельца удалить нельзя).")
