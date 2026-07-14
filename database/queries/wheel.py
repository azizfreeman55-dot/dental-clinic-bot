import random
import asyncpg
from typing import Optional


async def get_active_prizes(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT id, name, bonus_amount, weight, color FROM wheel_prizes WHERE active = TRUE ORDER BY id"
    )


async def get_spins_available(pool: asyncpg.Pool, patient_id: int) -> int:
    row = await pool.fetchrow(
        "SELECT spins_available FROM patient_wheel_credits WHERE patient_id = $1", patient_id
    )
    return row["spins_available"] if row else 0


async def grant_spin(pool_or_conn, patient_id: int, count: int = 1) -> None:
    """
    Начисляет вращение(я). Принимает либо pool, либо conn — так можно вызвать
    внутри уже открытой транзакции (например, при завершении визита).
    """
    await pool_or_conn.execute(
        """
        INSERT INTO patient_wheel_credits (patient_id, spins_available)
        VALUES ($1, $2)
        ON CONFLICT (patient_id) DO UPDATE
        SET spins_available = patient_wheel_credits.spins_available + $2
        """,
        patient_id, count,
    )


async def spin_wheel(pool: asyncpg.Pool, patient_id: int) -> Optional[dict]:
    """
    Атомарно списывает одно вращение и выбирает приз по весам.
    Возвращает None, если вращений не осталось.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            credit = await conn.fetchrow(
                "SELECT spins_available FROM patient_wheel_credits WHERE patient_id = $1 FOR UPDATE",
                patient_id,
            )
            if credit is None or credit["spins_available"] <= 0:
                return None

            prizes = await conn.fetch(
                "SELECT id, name, bonus_amount, weight FROM wheel_prizes WHERE active = TRUE ORDER BY id"
            )
            if not prizes:
                return None

            total_weight = sum(p["weight"] for p in prizes)
            roll = random.uniform(0, total_weight)
            cumulative = 0
            chosen = prizes[-1]
            for p in prizes:
                cumulative += p["weight"]
                if roll <= cumulative:
                    chosen = p
                    break

            await conn.execute(
                "UPDATE patient_wheel_credits SET spins_available = spins_available - 1 WHERE patient_id = $1",
                patient_id,
            )

            spin_id = await conn.fetchval(
                """
                INSERT INTO wheel_spins (patient_id, prize_id, bonus_amount)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                patient_id, chosen["id"], chosen["bonus_amount"],
            )

            if chosen["bonus_amount"] > 0:
                await conn.execute(
                    """
                    INSERT INTO bonus_transactions (patient_id, amount, type, description, related_id)
                    VALUES ($1, $2, 'wheel', 'Приз колеса фортуны', $3)
                    """,
                    patient_id, chosen["bonus_amount"], spin_id,
                )

            return {
                "spin_id": spin_id,
                "prize_id": chosen["id"],
                "prize_name": chosen["name"],
                "bonus_amount": chosen["bonus_amount"],
            }
