"""
Напоминания пациентам о предстоящем визите.

Джоба гоняется каждые 15 минут (см. регистрацию в bot.py) и проверяет
подтверждённые записи в ближайшие 3 дня. Как только до визита остаётся
<=24ч — отправляется первое напоминание, флаг reminder_24h_sent ставится в TRUE,
поэтому повторно оно не уйдёт. Аналогично для <=2ч.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg
from aiogram import Bot

logger = logging.getLogger(__name__)

TASHKENT = ZoneInfo("Asia/Tashkent")
MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def _fmt_dt(d, t) -> str:
    return f"{d.day} {MONTHS_RU[d.month - 1]} в {t.strftime('%H:%M')}"


async def send_reminders(bot: Bot, pool: asyncpg.Pool) -> None:
    now = datetime.now(TASHKENT)

    rows = await pool.fetch(
        """
        SELECT a.id, a.reminder_24h_sent, a.reminder_2h_sent,
               p.telegram_id AS patient_telegram_id,
               d.full_name AS doctor_name,
               s.name AS service_name,
               ds.date, ds.start_time
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        JOIN doctor_slots ds ON ds.id = a.slot_id
        WHERE a.status = 'confirmed'
          AND (a.reminder_24h_sent = FALSE OR a.reminder_2h_sent = FALSE)
          AND ds.date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '3 days'
        """
    )

    for r in rows:
        appt_dt = datetime.combine(r["date"], r["start_time"], tzinfo=TASHKENT)
        remaining = appt_dt - now

        if remaining.total_seconds() <= 0:
            continue  # запись уже в прошлом или идёт прямо сейчас — не шлём

        when_str = _fmt_dt(r["date"], r["start_time"])

        if not r["reminder_24h_sent"] and remaining <= timedelta(hours=24):
            text = (
                f"⏰ Напоминаем: завтра у вас приём!\n\n"
                f"👨‍⚕️ {r['doctor_name']}\n"
                f"💉 {r['service_name']}\n"
                f"📅 {when_str}"
            )
            try:
                await bot.send_message(r["patient_telegram_id"], text)
                await pool.execute(
                    "UPDATE appointments SET reminder_24h_sent = TRUE WHERE id = $1", r["id"]
                )
                logger.info(f"Отправлено 24ч напоминание для заявки {r['id']}")
            except Exception:
                logger.exception(f"Не удалось отправить 24ч напоминание для заявки {r['id']}")

        if not r["reminder_2h_sent"] and remaining <= timedelta(hours=2):
            text = (
                f"⏰ Напоминаем: приём уже через 2 часа!\n\n"
                f"👨‍⚕️ {r['doctor_name']}\n"
                f"💉 {r['service_name']}\n"
                f"📅 {when_str}\n\n"
                f"Ждём вас в клинике!"
            )
            try:
                await bot.send_message(r["patient_telegram_id"], text)
                await pool.execute(
                    "UPDATE appointments SET reminder_2h_sent = TRUE WHERE id = $1", r["id"]
                )
                logger.info(f"Отправлено 2ч напоминание для заявки {r['id']}")
            except Exception:
                logger.exception(f"Не удалось отправить 2ч напоминание для заявки {r['id']}")
