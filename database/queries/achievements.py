import asyncpg


async def get_patient_achievements_status(pool: asyncpg.Pool, patient_id: int) -> list[asyncpg.Record]:
    """Все достижения с пометкой, получено ли оно этим пациентом."""
    return await pool.fetch(
        """
        SELECT a.id, a.code, a.name, a.description, a.icon,
               pa.earned_at
        FROM achievements a
        LEFT JOIN patient_achievements pa
            ON pa.achievement_id = a.id AND pa.patient_id = $1
        ORDER BY a.sort_order
        """,
        patient_id,
    )


async def check_and_award_achievements(pool: asyncpg.Pool, patient_id: int) -> list[asyncpg.Record]:
    """
    Проверяет условия всех достижений для пациента и начисляет новые.
    Возвращает список ВНОВЬ полученных достижений (для уведомления в боте).
    Вызывается после завершения визита и после подтверждения рефералки.
    """
    patient = await pool.fetchrow(
        """
        SELECT p.total_visits, l.name AS level_name, l.sort_order AS level_sort_order,
               (SELECT COUNT(*) FROM referrals r WHERE r.referrer_id = p.id AND r.status = 'rewarded') AS successful_referrals
        FROM patients p
        JOIN loyalty_levels l ON l.id = p.level_id
        WHERE p.id = $1
        """,
        patient_id,
    )
    if patient is None:
        return []

    already_earned = {
        r["code"] for r in await pool.fetch(
            """
            SELECT a.code FROM patient_achievements pa
            JOIN achievements a ON a.id = pa.achievement_id
            WHERE pa.patient_id = $1
            """,
            patient_id,
        )
    }

    to_award = []
    if patient["total_visits"] >= 1 and "first_visit" not in already_earned:
        to_award.append("first_visit")
    if patient["total_visits"] >= 5 and "loyal_client" not in already_earned:
        to_award.append("loyal_client")
    if patient["total_visits"] >= 10 and "best_client" not in already_earned:
        to_award.append("best_client")
    if patient["successful_referrals"] >= 1 and "friend_bringer" not in already_earned:
        to_award.append("friend_bringer")
    if patient["level_sort_order"] >= 3 and "gold_level" not in already_earned:  # Gold = 3-й уровень
        to_award.append("gold_level")
    if patient["level_sort_order"] >= 4 and "platinum_level" not in already_earned:  # Platinum = 4-й уровень
        to_award.append("platinum_level")

    if not to_award:
        return []

    newly_awarded = await pool.fetch(
        """
        INSERT INTO patient_achievements (patient_id, achievement_id)
        SELECT $1, a.id FROM achievements a WHERE a.code = ANY($2::text[])
        ON CONFLICT DO NOTHING
        RETURNING achievement_id
        """,
        patient_id, to_award,
    )

    if not newly_awarded:
        return []

    ids = [r["achievement_id"] for r in newly_awarded]
    return await pool.fetch("SELECT * FROM achievements WHERE id = ANY($1::int[])", ids)
