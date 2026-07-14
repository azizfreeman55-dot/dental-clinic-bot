import asyncpg
from datetime import date


def _current_period_key(period: str) -> str:
    if period == "monthly":
        today = date.today()
        return f"{today.year}-{today.month:02d}"
    return "once"


async def _compute_progress(conn_or_pool, patient_id: int, mission: asyncpg.Record) -> int:
    monthly = mission["period"] == "monthly"

    if mission["metric"] == "referrals":
        if monthly:
            query = """
                SELECT COUNT(*) FROM referrals
                WHERE referrer_id = $1 AND status = 'rewarded'
                  AND date_trunc('month', rewarded_at) = date_trunc('month', CURRENT_DATE)
            """
        else:
            query = "SELECT COUNT(*) FROM referrals WHERE referrer_id = $1 AND status = 'rewarded'"
    else:  # visits
        if monthly:
            query = """
                SELECT COUNT(*) FROM appointments
                WHERE patient_id = $1 AND status = 'completed'
                  AND date_trunc('month', updated_at) = date_trunc('month', CURRENT_DATE)
            """
        else:
            query = "SELECT COUNT(*) FROM appointments WHERE patient_id = $1 AND status = 'completed'"

    return await conn_or_pool.fetchval(query, patient_id)


async def get_patient_missions_status(pool: asyncpg.Pool, patient_id: int) -> list[dict]:
    missions = await pool.fetch("SELECT * FROM missions WHERE active = TRUE ORDER BY sort_order")
    result = []

    for m in missions:
        period_key = _current_period_key(m["period"])
        progress = await _compute_progress(pool, patient_id, m)
        completed_row = await pool.fetchrow(
            "SELECT completed FROM patient_missions WHERE patient_id = $1 AND mission_id = $2 AND period_key = $3",
            patient_id, m["id"], period_key,
        )
        result.append({
            "id": m["id"],
            "name": m["name"],
            "description": m["description"],
            "target_count": m["target_count"],
            "reward_bonus": m["reward_bonus"],
            "period": m["period"],
            "progress": min(progress, m["target_count"]),
            "completed": bool(completed_row and completed_row["completed"]),
        })

    return result


async def check_and_award_missions(pool: asyncpg.Pool, patient_id: int) -> list[dict]:
    """
    Проверяет прогресс всех активных миссий и начисляет награду за только что выполненные.
    Возвращает список вновь выполненных миссий (для уведомления).
    """
    missions = await pool.fetch("SELECT * FROM missions WHERE active = TRUE")
    newly_completed = []

    for m in missions:
        period_key = _current_period_key(m["period"])

        async with pool.acquire() as conn:
            async with conn.transaction():
                existing = await conn.fetchrow(
                    """
                    SELECT id, completed FROM patient_missions
                    WHERE patient_id = $1 AND mission_id = $2 AND period_key = $3
                    FOR UPDATE
                    """,
                    patient_id, m["id"], period_key,
                )
                if existing and existing["completed"]:
                    continue  # уже выполнена и награждена в этом периоде

                progress = await _compute_progress(conn, patient_id, m)
                if progress < m["target_count"]:
                    continue  # ещё не выполнена

                if existing:
                    await conn.execute(
                        "UPDATE patient_missions SET completed = TRUE, completed_at = now() WHERE id = $1",
                        existing["id"],
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO patient_missions (patient_id, mission_id, period_key, completed, completed_at)
                        VALUES ($1, $2, $3, TRUE, now())
                        """,
                        patient_id, m["id"], period_key,
                    )

                await conn.execute(
                    """
                    INSERT INTO bonus_transactions (patient_id, amount, type, description, related_id)
                    VALUES ($1, $2, 'mission', $3, $4)
                    """,
                    patient_id, m["reward_bonus"], f"Миссия: {m['name']}", m["id"],
                )

                newly_completed.append({"name": m["name"], "reward_bonus": m["reward_bonus"]})

    return newly_completed
