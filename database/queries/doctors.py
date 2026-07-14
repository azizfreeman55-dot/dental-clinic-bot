import asyncpg
from datetime import date, timedelta


async def get_active_services(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT id, name, price, duration_min FROM services WHERE active = TRUE ORDER BY category, name"
    )


async def get_doctors_for_service(pool: asyncpg.Pool, service_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT d.id, d.full_name, d.specialization, d.photo_url,
               (SELECT MIN(t.start_time) FROM doctor_schedule_templates t
                WHERE t.doctor_id = d.id AND t.active = TRUE) AS shift_start
        FROM doctors d
        JOIN doctor_services ds ON ds.doctor_id = d.id
        WHERE ds.service_id = $1 AND d.active = TRUE
        ORDER BY shift_start, d.full_name
        """,
        service_id,
    )


def shift_label(shift_start) -> str:
    """shift_start — time начала смены врача. До полудня — дневная, после — вечерняя."""
    if shift_start is None:
        return ""
    return "Дневная смена (9:00–18:00)" if shift_start.hour < 12 else "Вечерняя смена (18:00–24:00)"


async def get_available_dates(pool: asyncpg.Pool, doctor_id: int, days_ahead: int = 14) -> list[date]:
    """Даты в ближайшие N дней, где у врача есть хотя бы один свободный слот."""
    rows = await pool.fetch(
        """
        SELECT DISTINCT date FROM doctor_slots
        WHERE doctor_id = $1
          AND is_booked = FALSE
          AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + $2::int
        ORDER BY date
        """,
        doctor_id, days_ahead,
    )
    return [r["date"] for r in rows]


async def get_service(pool: asyncpg.Pool, service_id: int) -> asyncpg.Record:
    return await pool.fetchrow("SELECT * FROM services WHERE id = $1", service_id)


async def get_doctor(pool: asyncpg.Pool, doctor_id: int) -> asyncpg.Record:
    return await pool.fetchrow("SELECT * FROM doctors WHERE id = $1", doctor_id)


async def get_slot(pool: asyncpg.Pool, slot_id: int) -> asyncpg.Record:
    return await pool.fetchrow("SELECT * FROM doctor_slots WHERE id = $1", slot_id)
