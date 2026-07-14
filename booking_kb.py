import asyncpg
from typing import Optional


async def get_free_slots(pool: asyncpg.Pool, doctor_id: int, date) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT id, start_time, end_time
        FROM doctor_slots
        WHERE doctor_id = $1 AND date = $2 AND is_booked = FALSE
        ORDER BY start_time
        """,
        doctor_id, date,
    )


async def book_slot(
    pool: asyncpg.Pool,
    patient_id: int,
    doctor_id: int,
    service_id: int,
    slot_id: int,
) -> Optional[int]:
    """
    Атомарно бронирует слот и создаёт запись.
    Возвращает appointment_id или None, если слот уже занят
    (кто-то другой успел забронировать между показом экрана и нажатием кнопки).

    Вся операция — одна транзакция, слот блокируется через SELECT ... FOR UPDATE,
    поэтому даже при одновременном нажатии двумя пациентами второй гарантированно получит None.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            slot = await conn.fetchrow(
                """
                SELECT id FROM doctor_slots
                WHERE id = $1 AND is_booked = FALSE
                FOR UPDATE
                """,
                slot_id,
            )
            if slot is None:
                return None  # слот уже занят другим пациентом — сообщи пользователю "к сожалению, слот только что заняли"

            appointment_id = await conn.fetchval(
                """
                INSERT INTO appointments (patient_id, doctor_id, service_id, slot_id, status)
                VALUES ($1, $2, $3, $4, 'pending')
                RETURNING id
                """,
                patient_id, doctor_id, service_id, slot_id,
            )

            await conn.execute(
                """
                UPDATE doctor_slots
                SET is_booked = TRUE, appointment_id = $1
                WHERE id = $2
                """,
                appointment_id, slot_id,
            )

            return appointment_id


async def confirm_appointment(pool: asyncpg.Pool, appointment_id: int) -> None:
    """Админ подтверждает запись — вызывается из bot_handlers/admin/."""
    await pool.execute(
        "UPDATE appointments SET status = 'confirmed', updated_at = now() WHERE id = $1",
        appointment_id,
    )


async def cancel_appointment(pool: asyncpg.Pool, appointment_id: int, by_admin: bool) -> None:
    """Отменяет запись и освобождает слот обратно."""
    status = "cancelled_by_admin" if by_admin else "cancelled_by_patient"
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE appointments SET status = $1, updated_at = now() WHERE id = $2",
                status, appointment_id,
            )
            await conn.execute(
                """
                UPDATE doctor_slots
                SET is_booked = FALSE, appointment_id = NULL
                WHERE appointment_id = $1
                """,
                appointment_id,
            )
