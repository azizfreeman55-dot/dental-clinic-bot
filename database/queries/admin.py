import asyncpg
from typing import Optional


async def is_admin(pool: asyncpg.Pool, telegram_id: int) -> bool:
    row = await pool.fetchrow("SELECT 1 FROM admins WHERE telegram_id = $1", telegram_id)
    return row is not None


async def get_admin_telegram_ids(pool: asyncpg.Pool) -> list[int]:
    rows = await pool.fetch("SELECT telegram_id FROM admins")
    return [r["telegram_id"] for r in rows]


async def ensure_admin(pool: asyncpg.Pool, telegram_id: int, full_name: str = "Owner") -> None:
    """
    Вызывается при каждом старте бота, если задана переменная окружения ADMIN_TELEGRAM_ID.
    Идемпотентно — если админ уже есть, ничего не делает.
    """
    await pool.execute(
        """
        INSERT INTO admins (telegram_id, full_name, role)
        VALUES ($1, $2, 'owner')
        ON CONFLICT (telegram_id) DO NOTHING
        """,
        telegram_id, full_name,
    )


async def get_pending_redemptions(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT r.id, r.cost_bonuses, r.redeemed_at,
               p.full_name AS patient_name, p.telegram_id AS patient_telegram_id, p.phone,
               g.name AS gift_name
        FROM gift_redemptions r
        JOIN patients p ON p.id = r.patient_id
        JOIN gifts_catalog g ON g.id = r.gift_id
        WHERE r.status = 'pending'
        ORDER BY r.redeemed_at
        """
    )


async def mark_redemption_used(pool: asyncpg.Pool, redemption_id: int) -> bool:
    result = await pool.execute(
        "UPDATE gift_redemptions SET status = 'used', used_at = now() WHERE id = $1 AND status = 'pending'",
        redemption_id,
    )
    return result.endswith("1")


async def get_admin_stats(pool: asyncpg.Pool) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM appointments WHERE status = 'pending') AS pending_count,
            (SELECT COUNT(*) FROM appointments WHERE status = 'confirmed') AS confirmed_count,
            (SELECT COUNT(*) FROM appointments WHERE status = 'awaiting_reschedule') AS awaiting_reschedule_count,
            (SELECT COUNT(*) FROM appointments WHERE status = 'completed' AND updated_at::date = CURRENT_DATE) AS completed_today,
            (SELECT COUNT(*) FROM appointments WHERE status = 'completed'
                AND date_trunc('month', updated_at) = date_trunc('month', CURRENT_DATE)) AS completed_this_month,
            (SELECT COALESCE(SUM(amount_paid), 0) FROM treatment_history
                WHERE date_trunc('month', created_at) = date_trunc('month', CURRENT_DATE)) AS revenue_this_month,
            (SELECT COUNT(*) FROM patients) AS total_patients,
            (SELECT COUNT(*) FROM patients WHERE created_at::date = CURRENT_DATE) AS new_patients_today
        """
    )


async def get_appointments_by_status(pool: asyncpg.Pool, status: str, limit: int = 100) -> list[asyncpg.Record]:
    valid_statuses = {"pending", "confirmed", "completed", "cancelled_by_patient", "cancelled_by_admin", "awaiting_reschedule"}
    if status not in valid_statuses:
        return []

    order = "ds.date ASC, ds.start_time ASC" if status in ("pending", "confirmed", "awaiting_reschedule") else "a.updated_at DESC"

    return await pool.fetch(
        f"""
        SELECT a.id, a.status, a.created_at, a.updated_at,
               p.full_name AS patient_name, p.telegram_id AS patient_telegram_id, p.phone,
               d.full_name AS doctor_name,
               s.name AS service_name, s.price,
               ds.date, ds.start_time
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        JOIN doctor_slots ds ON ds.id = a.slot_id
        WHERE a.status = $1
        ORDER BY {order}
        LIMIT $2
        """,
        status, limit,
    )


async def get_appointments_for_date(pool: asyncpg.Pool, target_date) -> list[asyncpg.Record]:
    """Все записи на конкретную дату, по всем врачам — для календаря в админке."""
    return await pool.fetch(
        """
        SELECT a.id, a.status,
               p.full_name AS patient_name, p.telegram_id AS patient_telegram_id, p.phone,
               d.full_name AS doctor_name, d.id AS doctor_id,
               s.name AS service_name, s.price,
               ds.start_time
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        JOIN doctor_slots ds ON ds.id = a.slot_id
        WHERE ds.date = $1
          AND a.status IN ('pending', 'confirmed', 'completed', 'awaiting_reschedule')
        ORDER BY d.full_name, ds.start_time
        """,
        target_date,
    )


async def get_pending_appointments(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT a.id, a.created_at,
               p.full_name AS patient_name, p.telegram_id AS patient_telegram_id,
               d.full_name AS doctor_name,
               s.name AS service_name, s.price,
               ds.date, ds.start_time
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        JOIN doctor_slots ds ON ds.id = a.slot_id
        WHERE a.status = 'pending'
        ORDER BY ds.date, ds.start_time
        """
    )


async def get_confirmed_upcoming_appointments(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """Подтверждённые записи, которые ещё не отмечены как завершённые — кандидаты на 'приём состоялся'."""
    return await pool.fetch(
        """
        SELECT a.id, p.full_name AS patient_name, p.telegram_id AS patient_telegram_id,
               d.full_name AS doctor_name, s.name AS service_name, s.price,
               ds.date, ds.start_time
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        JOIN doctor_slots ds ON ds.id = a.slot_id
        WHERE a.status = 'confirmed'
        ORDER BY ds.date, ds.start_time
        """
    )


async def get_appointment_full(pool: asyncpg.Pool, appointment_id: int) -> Optional[asyncpg.Record]:
    return await pool.fetchrow(
        """
        SELECT a.id, a.status, a.patient_id, a.doctor_id, a.created_at, a.admin_comment,
               p.full_name AS patient_name, p.telegram_id AS patient_telegram_id,
               p.phone, p.id AS patient_pk, p.bonus_balance, p.lifetime_bonus_earned,
               p.total_visits, p.created_at AS patient_since,
               l.name AS level_name, l.bonus_percent,
               d.full_name AS doctor_name, d.specialization AS doctor_specialization,
               (SELECT MIN(t.start_time) FROM doctor_schedule_templates t
                WHERE t.doctor_id = d.id AND t.active = TRUE) AS doctor_shift_start,
               s.id AS service_id, s.name AS service_name, s.price, s.description AS service_description,
               ds.date, ds.start_time,
               (SELECT COUNT(*) FROM appointments a2
                WHERE a2.patient_id = a.patient_id AND a2.status = 'completed') AS completed_visits_count,
               (SELECT r.status FROM referrals r WHERE r.referred_id = a.patient_id) AS referral_status
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN loyalty_levels l ON l.id = p.level_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        JOIN doctor_slots ds ON ds.id = a.slot_id
        WHERE a.id = $1
        """,
        appointment_id,
    )


async def complete_appointment_with_bonus(
    pool: asyncpg.Pool,
    appointment_id: int,
    patient_id: int,
    doctor_id: int,
    amount_paid: float,
    bonus_percent: float,
) -> dict:
    """
    Отмечает визит завершённым, пишет в treatment_history и начисляет бонусы
    через bonus_transactions (триггер в БД сам обновит баланс и уровень пациента).

    Если это ПЕРВЫЙ визит пациента и он пришёл по реферальной ссылке —
    дополнительно начисляет бонусы и ему, и пригласившему, и уведомляет об этом (возвращает данные для уведомления).

    Возвращает dict: {bonuses_earned, referral_applied, referrer_telegram_id, referrer_bonus, referred_bonus}
    """
    bonuses_earned = round(amount_paid * float(bonus_percent) / 100)
    result = {
        "bonuses_earned": bonuses_earned,
        "referral_applied": False,
        "referrer_telegram_id": None,
        "referrer_bonus": 0,
        "referred_bonus": 0,
    }

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE appointments SET status = 'completed', updated_at = now() WHERE id = $1",
                appointment_id,
            )
            await conn.execute(
                """
                INSERT INTO treatment_history (appointment_id, patient_id, doctor_id, amount_paid, bonuses_earned)
                VALUES ($1, $2, $3, $4, $5)
                """,
                appointment_id, patient_id, doctor_id, amount_paid, bonuses_earned,
            )
            await conn.execute(
                """
                INSERT INTO bonus_transactions (patient_id, amount, type, description, related_id)
                VALUES ($1, $2, 'earn_visit', 'Начисление за визит', $3)
                """,
                patient_id, bonuses_earned, appointment_id,
            )

            visits_before = await conn.fetchval(
                "SELECT total_visits FROM patients WHERE id = $1", patient_id
            )

            await conn.execute(
                "UPDATE patients SET total_visits = total_visits + 1 WHERE id = $1",
                patient_id,
            )

            # это был первый визит пациента (visits_before == 0) — проверяем реферальный статус
            if visits_before == 0:
                referral = await conn.fetchrow(
                    """
                    SELECT id, referrer_id, referrer_bonus, referred_bonus
                    FROM referrals
                    WHERE referred_id = $1 AND status = 'pending'
                    FOR UPDATE
                    """,
                    patient_id,
                )

                if referral:
                    await conn.execute(
                        "UPDATE referrals SET status = 'rewarded', rewarded_at = now() WHERE id = $1",
                        referral["id"],
                    )
                    await conn.execute(
                        """
                        INSERT INTO bonus_transactions (patient_id, amount, type, description, related_id)
                        VALUES ($1, $2, 'referral', 'Бонус за приглашённого друга', $3)
                        """,
                        referral["referrer_id"], referral["referrer_bonus"], referral["id"],
                    )
                    await conn.execute(
                        """
                        INSERT INTO bonus_transactions (patient_id, amount, type, description, related_id)
                        VALUES ($1, $2, 'referral', 'Бонус за первый визит по приглашению', $3)
                        """,
                        patient_id, referral["referred_bonus"], referral["id"],
                    )

                    referrer_telegram_id = await conn.fetchval(
                        "SELECT telegram_id FROM patients WHERE id = $1", referral["referrer_id"]
                    )

                    result["referral_applied"] = True
                    result["referrer_telegram_id"] = referrer_telegram_id
                    result["referrer_bonus"] = referral["referrer_bonus"]
                    result["referred_bonus"] = referral["referred_bonus"]

    return result
