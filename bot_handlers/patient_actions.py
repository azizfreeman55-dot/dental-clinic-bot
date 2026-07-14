from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from database.pool import get_pool
from database.queries.admin import get_appointment_full, get_admin_telegram_ids
from database.queries.appointments import confirm_reschedule, decline_reschedule

router = Router(name="patient_actions")

MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def _fmt_date(d, t):
    return f"{d.day} {MONTHS_RU[d.month - 1]} в {t.strftime('%H:%M')}"


@router.callback_query(F.data.startswith("pt:resched_yes:"))
async def patient_accepts_reschedule(callback: CallbackQuery, bot: Bot):
    appointment_id = int(callback.data.split(":")[2])
    pool = get_pool()

    a = await get_appointment_full(pool, appointment_id)
    if a is None or a["patient_telegram_id"] != callback.from_user.id:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if a["status"] != "awaiting_reschedule":
        await callback.answer("Это предложение уже неактуально", show_alert=True)
        return

    await confirm_reschedule(pool, appointment_id)

    await callback.message.edit_text(
        f"✅ Отлично! Запись подтверждена на {_fmt_date(a['date'], a['start_time'])}.\n"
        f"👨‍⚕️ {a['doctor_name']} · {a['service_name']}\n\nЖдём вас в клинике!"
    )
    await callback.answer()

    # уведомляем админов, что перенос принят
    admin_ids = await get_admin_telegram_ids(pool)
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"✅ {a['patient_name']} подтвердил(а) перенос на {_fmt_date(a['date'], a['start_time'])}",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("pt:resched_no:"))
async def patient_declines_reschedule(callback: CallbackQuery, bot: Bot):
    appointment_id = int(callback.data.split(":")[2])
    pool = get_pool()

    a = await get_appointment_full(pool, appointment_id)
    if a is None or a["patient_telegram_id"] != callback.from_user.id:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if a["status"] != "awaiting_reschedule":
        await callback.answer("Это предложение уже неактуально", show_alert=True)
        return

    await decline_reschedule(pool, appointment_id)

    await callback.message.edit_text(
        "Хорошо, это время отменено. Вы можете выбрать другое в разделе «Записаться на приём» в личном кабинете."
    )
    await callback.answer()

    admin_ids = await get_admin_telegram_ids(pool)
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"❌ {a['patient_name']} отказался(ась) от предложенного времени {_fmt_date(a['date'], a['start_time'])}",
            )
        except Exception:
            pass
