import asyncpg
from typing import Optional


async def get_active_gifts(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT * FROM gifts_catalog WHERE active = TRUE ORDER BY sort_order, cost_bonuses"
    )


async def get_gift(pool: asyncpg.Pool, gift_id: int) -> Optional[asyncpg.Record]:
    return await pool.fetchrow("SELECT * FROM gifts_catalog WHERE id = $1", gift_id)


async def redeem_gift(pool: asyncpg.Pool, patient_id: int, gift_id: int) -> Optional[int]:
    """
    Атомарно списывает бонусы и создаёт погашение.
    Возвращает id погашения, либо None, если баланса не хватает
    (проверка и списание в одной транзакции с блокировкой строки — гонка при двойном клике исключена).
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            gift = await conn.fetchrow(
                "SELECT cost_bonuses FROM gifts_catalog WHERE id = $1 AND active = TRUE", gift_id
            )
            if gift is None:
                return None

            patient = await conn.fetchrow(
                "SELECT bonus_balance FROM patients WHERE id = $1 FOR UPDATE", patient_id
            )
            if patient is None or patient["bonus_balance"] < gift["cost_bonuses"]:
                return None

            redemption_id = await conn.fetchval(
                """
                INSERT INTO gift_redemptions (patient_id, gift_id, cost_bonuses, status)
                VALUES ($1, $2, $3, 'pending')
                RETURNING id
                """,
                patient_id, gift_id, gift["cost_bonuses"],
            )

            # списание идёт через bonus_transactions — триггер в БД сам уменьшит bonus_balance.
            # lifetime_bonus_earned (используется для уровня) не трогаем — уровень не понижается от трат.
            await conn.execute(
                """
                INSERT INTO bonus_transactions (patient_id, amount, type, description, related_id)
                VALUES ($1, $2, 'spend_gift', 'Обмен на подарок', $3)
                """,
                patient_id, -gift["cost_bonuses"], redemption_id,
            )

            return redemption_id


async def get_patient_redemptions(pool: asyncpg.Pool, patient_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT r.id, r.status, r.cost_bonuses, r.redeemed_at, r.used_at,
               g.name AS gift_name, g.description AS gift_description
        FROM gift_redemptions r
        JOIN gifts_catalog g ON g.id = r.gift_id
        WHERE r.patient_id = $1
        ORDER BY r.redeemed_at DESC
        """,
        patient_id,
    )
