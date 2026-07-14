"""
slot_generator.py

Раз в сутки (и один раз при старте приложения) генерирует doctor_slots
на N дней вперёд из doctor_schedule_templates.

Идемпотентно: повторный запуск не создаёт дублей благодаря
UNIQUE (doctor_id, date, start_time) в БД + ON CONFLICT DO NOTHING.
Это значит джобу можно безопасно гонять хоть каждый час — лишнего не создаст.
"""

import asyncpg
from datetime import date, timedelta, datetime, time as dt_time
import logging

logger = logging.getLogger(__name__)

DAYS_AHEAD_DEFAULT = 30  # горизонт, на который держим слоты открытыми


def _generate_time_slots(start: dt_time, end: dt_time, duration_min: int) -> list[tuple[dt_time, dt_time]]:
    """Нарезает интервал [start, end) на слоты по duration_min минут."""
    slots = []
    cursor = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    step = timedelta(minutes=duration_min)

    while cursor + step <= end_dt:
        slot_start = cursor.time()
        slot_end = (cursor + step).time()
        slots.append((slot_start, slot_end))
        cursor += step

    return slots


async def generate_slots_for_doctor(
    pool: asyncpg.Pool,
    doctor_id: int,
    days_ahead: int = DAYS_AHEAD_DEFAULT,
) -> int:
    """
    Генерирует слоты для одного врача на days_ahead дней вперёд, начиная с завтра.
    Возвращает количество реально вставленных (новых) слотов.
    """
    templates = await pool.fetch(
        """
        SELECT weekday, start_time, end_time, slot_duration_min
        FROM doctor_schedule_templates
        WHERE doctor_id = $1 AND active = TRUE
        """,
        doctor_id,
    )

    if not templates:
        return 0

    # weekday -> список шаблонов (на случай двух смен в один день, напр. 9-13 и 15-19)
    templates_by_weekday: dict[int, list[asyncpg.Record]] = {}
    for t in templates:
        templates_by_weekday.setdefault(t["weekday"], []).append(t)

    rows_to_insert: list[tuple] = []
    today = date.today()

    for offset in range(1, days_ahead + 1):  # с завтрашнего дня — сегодняшний уже мог начаться
        target_date = today + timedelta(days=offset)
        weekday = target_date.weekday()  # 0=понедельник, совпадает со схемой

        for tpl in templates_by_weekday.get(weekday, []):
            for slot_start, slot_end in _generate_time_slots(
                tpl["start_time"], tpl["end_time"], tpl["slot_duration_min"]
            ):
                rows_to_insert.append((doctor_id, target_date, slot_start, slot_end))

    if not rows_to_insert:
        return 0

    async with pool.acquire() as conn:
        result = await conn.executemany(
            """
            INSERT INTO doctor_slots (doctor_id, date, start_time, end_time)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (doctor_id, date, start_time) DO NOTHING
            """,
            rows_to_insert,
        )

    logger.info(f"Doctor {doctor_id}: сгенерировано попыток вставки {len(rows_to_insert)} слотов")
    return len(rows_to_insert)


async def generate_slots_for_all_doctors(pool: asyncpg.Pool, days_ahead: int = DAYS_AHEAD_DEFAULT) -> None:
    """Вызывается джобой APScheduler и один раз при старте приложения."""
    doctor_ids = await pool.fetch("SELECT id FROM doctors WHERE active = TRUE")

    for row in doctor_ids:
        try:
            await generate_slots_for_doctor(pool, row["id"], days_ahead)
        except Exception:
            logger.exception(f"Ошибка генерации слотов для врача {row['id']}")

    logger.info(f"Генерация слотов завершена для {len(doctor_ids)} врачей")


async def cleanup_expired_unbooked_slots(pool: asyncpg.Pool) -> None:
    """
    Опционально: удаляет прошедшие незабронированные слоты, чтобы таблица не росла бесконечно.
    Забронированные (is_booked=TRUE) прошедшие слоты НЕ трогаем — они нужны для истории appointments.
    """
    deleted = await pool.execute(
        """
        DELETE FROM doctor_slots
        WHERE date < CURRENT_DATE AND is_booked = FALSE
        """
    )
    logger.info(f"Очистка старых слотов: {deleted}")


def setup_scheduler_jobs(scheduler, pool: asyncpg.Pool) -> None:
    """
    Регистрирует джобы в уже созданном AsyncIOScheduler (из bot.py).
    Пример использования в bot.py:

        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
        setup_scheduler_jobs(scheduler, pool)
        scheduler.start()
    """
    scheduler.add_job(
        generate_slots_for_all_doctors,
        "cron",
        hour=3,
        minute=0,
        args=[pool],
        id="generate_slots_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_expired_unbooked_slots,
        "cron",
        hour=3,
        minute=30,
        args=[pool],
        id="cleanup_expired_slots",
        replace_existing=True,
    )
