import asyncpg
from typing import Optional


async def get_patient_by_telegram_id(pool: asyncpg.Pool, telegram_id: int) -> Optional[asyncpg.Record]:
    return await pool.fetchrow(
        "SELECT * FROM patients WHERE telegram_id = $1", telegram_id
    )


async def get_or_create_patient(
    pool: asyncpg.Pool,
    telegram_id: int,
    full_name: str,
    referrer_telegram_id: Optional[int] = None,
) -> tuple[asyncpg.Record, bool]:
    """
    Возвращает (patient, created).
    Если referrer_telegram_id указан и это первая регистрация — привязывает реферера
    (саму бонусную начисление за рефералку делаем отдельно, в шаге 5 плана — таблица referrals).
    """
    existing = await get_patient_by_telegram_id(pool, telegram_id)
    if existing:
        return existing, False

    referrer_id = None
    if referrer_telegram_id and referrer_telegram_id != telegram_id:
        referrer = await get_patient_by_telegram_id(pool, referrer_telegram_id)
        if referrer:
            referrer_id = referrer["id"]

    row = await pool.fetchrow(
        """
        INSERT INTO patients (telegram_id, full_name, referrer_id, level_id)
        VALUES ($1, $2, $3, (SELECT id FROM loyalty_levels ORDER BY sort_order LIMIT 1))
        RETURNING *
        """,
        telegram_id, full_name, referrer_id,
    )
    return row, True


async def get_patient_level_info(pool: asyncpg.Pool, patient_id: int) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        SELECT p.bonus_balance, p.lifetime_bonus_earned, l.name AS level_name,
               l.bonus_percent, l.benefits,
               (SELECT min_lifetime_bonus_earned FROM loyalty_levels
                WHERE sort_order = (SELECT sort_order + 1 FROM loyalty_levels WHERE id = p.level_id)) AS next_level_threshold
        FROM patients p
        JOIN loyalty_levels l ON l.id = p.level_id
        WHERE p.id = $1
        """,
        patient_id,
    )
