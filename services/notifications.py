import logging
import asyncpg
from aiogram import Bot

from database.queries.admin import get_appointment_full, get_admin_telegram_ids

logger = logging.getLogger(__name__)

MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


async def notify_admins_new_appointment(bot: Bot, pool: asyncpg.Pool, appointment_id: int) -> None:
    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        return

    admin_ids = await get_admin_telegram_ids(pool)
    if not admin_ids:
        logger.warning("Новая заявка создана, но в таблице admins нет ни одного админа для уведомления")
        return

    price_str = f"{int(a['price']):,}".replace(",", " ")
    balance_str = f"{a['bonus_balance']:,}".replace(",", " ")
    is_first_visit = a["completed_visits_count"] == 0

    phone_line = f"\n📱 {a['phone']}" if a["phone"] else ""
    visit_note = "первый визит 🆕" if is_first_visit else f"визитов: {a['completed_visits_count']}"

    text = (
        f"🆕 Новая заявка на запись!\n\n"
        f"👤 {a['patient_name']}{phone_line}\n"
        f"⭐ Уровень {a['level_name']} · баланс {balance_str} · {visit_note}\n\n"
        f"👨‍⚕️ {a['doctor_name']} ({a['doctor_specialization']})\n"
        f"💉 {a['service_name']} — {price_str} сум\n"
        f"📅 {a['date'].day} {MONTHS_RU[a['date'].month - 1]} в {a['start_time'].strftime('%H:%M')}\n\n"
        f"Подтвердить или отклонить: /admin"
    )

    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logger.exception(f"Не удалось отправить уведомление админу {admin_id}")
