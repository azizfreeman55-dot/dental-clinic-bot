from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.pool import get_pool
from database.queries.admin import (
    get_pending_appointments, get_confirmed_upcoming_appointments,
    get_appointment_full, complete_appointment_with_bonus,
)
from database.queries.appointments import (
    confirm_appointment, cancel_appointment,
    propose_reschedule,
)
from database.queries.doctors import get_available_dates, shift_label
from database.queries.appointments import get_free_slots
from database.queries.achievements import check_and_award_achievements
from bot_handlers.admin.filters import IsAdmin
from states import AdminStates

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def _fmt_date(d, t):
    return f"{d.day} {MONTHS_RU[d.month - 1]} в {t.strftime('%H:%M')}"


WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _fmt_date_only(d):
    return f"{WEEKDAYS_RU[d.weekday()]} {d.day} {MONTHS_RU[d.month - 1]}"


def admin_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🆕 Заявки на подтверждение", callback_data="adm:pending")
    b.button(text="✅ Отметить визит завершённым", callback_data="adm:confirmed")
    b.adjust(1)
    return b.as_markup()


@router.message(Command("admin"))
async def admin_menu(message: Message):
    await message.answer("Админ-панель:", reply_markup=admin_menu_kb())


# ---------- Список заявок на подтверждение ----------

@router.callback_query(F.data == "adm:pending")
async def list_pending(callback: CallbackQuery):
    pool = get_pool()
    appointments = await get_pending_appointments(pool)

    if not appointments:
        await callback.message.edit_text("Новых заявок нет 👍", reply_markup=admin_menu_kb())
        await callback.answer()
        return

    b = InlineKeyboardBuilder()
    for a in appointments:
        label = f"{a['patient_name']} — {a['service_name']} — {_fmt_date(a['date'], a['start_time'])}"
        b.button(text=label, callback_data=f"adm:view:{a['id']}")
    b.button(text="⬅️ Назад", callback_data="adm:menu")
    b.adjust(1)

    await callback.message.edit_text(f"Заявок на подтверждение: {len(appointments)}", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data == "adm:menu")
async def back_to_admin_menu(callback: CallbackQuery):
    await callback.message.edit_text("Админ-панель:", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:view:"))
async def view_appointment(callback: CallbackQuery):
    from database.queries.doctors import shift_label

    appointment_id = int(callback.data.split(":")[2])
    pool = get_pool()
    a = await get_appointment_full(pool, appointment_id)

    if a is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    price_str = f"{int(a['price']):,}".replace(",", " ")
    balance_str = f"{a['bonus_balance']:,}".replace(",", " ")

    is_first_visit = a["completed_visits_count"] == 0
    referral_note = ""
    if a["referral_status"] == "pending":
        referral_note = "\n🔗 Пришёл по реферальной ссылке — при завершении визита сработает бонус за приглашение"
    elif a["referral_status"] == "rewarded":
        referral_note = "\n🔗 Пришёл по реферальной ссылке (бонус уже начислен ранее)"

    phone_line = f"\n📱 Телефон: {a['phone']}" if a["phone"] else ""
    description_line = f"\nℹ️ {a['service_description']}" if a["service_description"] else ""

    text = (
        f"📋 Заявка №{a['id']}  ·  статус: {a['status']}\n"
        f"{'─' * 20}\n"
        f"👤 КЛИЕНТ\n"
        f"Имя: {a['patient_name']}{phone_line}\n"
        f"Уровень: {a['level_name']} ({a['bonus_percent']}% с визита)\n"
        f"Баланс бонусов: {balance_str}\n"
        f"Завершённых визитов: {a['completed_visits_count']}"
        f"{' (это будет первый визит)' if is_first_visit else ''}"
        f"{referral_note}\n"
        f"{'─' * 20}\n"
        f"👨‍⚕️ ВРАЧ\n"
        f"{a['doctor_name']} — {a['doctor_specialization']}\n"
        f"{shift_label(a['doctor_shift_start'])}\n"
        f"{'─' * 20}\n"
        f"💉 УСЛУГА\n"
        f"{a['service_name']} — {price_str} сум{description_line}\n"
        f"{'─' * 20}\n"
        f"📅 Дата приёма: {_fmt_date(a['date'], a['start_time'])}\n"
        f"🕐 Заявка создана: {a['created_at'].strftime('%d.%m %H:%M')}"
    )

    b = InlineKeyboardBuilder()
    if a["status"] == "pending":
        b.button(text="✅ Подтвердить", callback_data=f"adm:confirm:{a['id']}")
        b.button(text="❌ Отклонить", callback_data=f"adm:decline:{a['id']}")
    elif a["status"] == "confirmed":
        b.button(text="✅ Визит состоялся", callback_data=f"adm:complete:{a['id']}")
    b.button(text="⬅️ К списку", callback_data="adm:pending")
    b.adjust(1)

    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()


# ---------- Подтверждение / отклонение ----------

@router.callback_query(F.data.startswith("adm:confirm:"))
async def do_confirm(callback: CallbackQuery, bot: Bot):
    appointment_id = int(callback.data.split(":")[2])
    pool = get_pool()

    a = await get_appointment_full(pool, appointment_id)
    await confirm_appointment(pool, appointment_id)

    await bot.send_message(
        a["patient_telegram_id"],
        f"✅ Ваша запись подтверждена!\n\n"
        f"👨‍⚕️ {a['doctor_name']}\n"
        f"📅 {_fmt_date(a['date'], a['start_time'])}\n\n"
        f"Ждём вас в клинике!",
    )

    await callback.answer("Запись подтверждена, пациент уведомлён")
    await list_pending(callback)


@router.callback_query(F.data.startswith("adm:decline:"))
async def decline_menu(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":")[2])

    b = InlineKeyboardBuilder()
    b.button(text="🔄 Предложить другое время", callback_data=f"adm:reschedule:{appointment_id}")
    b.button(text="❌ Просто отклонить", callback_data=f"adm:decline_now:{appointment_id}")
    b.button(text="⬅️ Назад", callback_data=f"adm:view:{appointment_id}")
    b.adjust(1)

    await callback.message.edit_text(
        "Отклонить заявку или предложить пациенту другое время?",
        reply_markup=b.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:decline_now:"))
async def do_decline(callback: CallbackQuery, bot: Bot):
    appointment_id = int(callback.data.split(":")[2])
    pool = get_pool()

    a = await get_appointment_full(pool, appointment_id)
    await cancel_appointment(pool, appointment_id, by_admin=True)

    await bot.send_message(
        a["patient_telegram_id"],
        f"К сожалению, ваша запись на {_fmt_date(a['date'], a['start_time'])} отклонена администратором. "
        f"Пожалуйста, выберите другое время в разделе «Записаться на приём».",
    )

    await callback.answer("Запись отклонена, пациент уведомлён")
    await list_pending(callback)


# ---------- Предложить другое время ----------

@router.callback_query(F.data.startswith("adm:reschedule:"))
async def reschedule_pick_date(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":")[2])
    pool = get_pool()

    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    dates = await get_available_dates(pool, a["doctor_id"])
    if not dates:
        await callback.answer("У этого врача нет свободных дат для переноса", show_alert=True)
        return

    b = InlineKeyboardBuilder()
    for d in dates:
        b.button(text=_fmt_date_only(d), callback_data=f"adm:resched_date:{appointment_id}:{d.isoformat()}")
    b.button(text="⬅️ Назад", callback_data=f"adm:decline:{appointment_id}")
    b.adjust(2)

    await callback.message.edit_text(
        f"Выберите новую дату для {a['patient_name']} ({a['doctor_name']}):",
        reply_markup=b.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:resched_date:"))
async def reschedule_pick_slot(callback: CallbackQuery):
    _, _, appointment_id, date_str = callback.data.split(":")
    appointment_id = int(appointment_id)
    from datetime import date as date_cls
    chosen_date = date_cls.fromisoformat(date_str)

    pool = get_pool()
    a = await get_appointment_full(pool, appointment_id)
    slots = await get_free_slots(pool, a["doctor_id"], chosen_date)

    if not slots:
        await callback.answer("На эту дату свободных слотов не осталось", show_alert=True)
        return

    b = InlineKeyboardBuilder()
    for s in slots:
        b.button(
            text=s["start_time"].strftime("%H:%M"),
            callback_data=f"adm:resched_slot:{appointment_id}:{s['id']}",
        )
    b.button(text="⬅️ Назад", callback_data=f"adm:reschedule:{appointment_id}")
    b.adjust(4)

    await callback.message.edit_text("Выберите время:", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:resched_slot:"))
async def reschedule_confirm(callback: CallbackQuery, bot: Bot):
    _, _, appointment_id, slot_id = callback.data.split(":")
    appointment_id = int(appointment_id)
    slot_id = int(slot_id)

    pool = get_pool()
    a = await get_appointment_full(pool, appointment_id)

    new_appointment_id = await propose_reschedule(
        pool,
        old_appointment_id=appointment_id,
        patient_id=a["patient_pk"],
        doctor_id=a["doctor_id"],
        service_id=a["service_id"],
        new_slot_id=slot_id,
    )

    if new_appointment_id is None:
        await callback.answer("Этот слот уже заняли, выберите другой", show_alert=True)
        return

    new_a = await get_appointment_full(pool, new_appointment_id)

    pb = InlineKeyboardBuilder()
    pb.button(text="✅ Подтверждаю", callback_data=f"pt:resched_yes:{new_appointment_id}")
    pb.button(text="❌ Не подходит, отменить", callback_data=f"pt:resched_no:{new_appointment_id}")
    pb.adjust(1)

    await bot.send_message(
        new_a["patient_telegram_id"],
        f"К сожалению, ваше время на {_fmt_date(a['date'], a['start_time'])} было занято.\n\n"
        f"Но у нас есть свободное время: <b>{_fmt_date(new_a['date'], new_a['start_time'])}</b> "
        f"у врача {new_a['doctor_name']} ({new_a['service_name']}).\n\n"
        f"Устроит вас такое время?",
        reply_markup=pb.as_markup(),
    )

    await callback.answer("Предложение отправлено пациенту")
    await callback.message.edit_text(
        f"✅ Пациенту {a['patient_name']} предложено новое время: {_fmt_date(new_a['date'], new_a['start_time'])}.\n"
        f"Ждём его ответа."
    )


# ---------- Завершение визита + начисление бонусов ----------

@router.callback_query(F.data == "adm:confirmed")
async def list_confirmed(callback: CallbackQuery):
    pool = get_pool()
    appointments = await get_confirmed_upcoming_appointments(pool)

    if not appointments:
        await callback.message.edit_text("Нет подтверждённых записей", reply_markup=admin_menu_kb())
        await callback.answer()
        return

    b = InlineKeyboardBuilder()
    for a in appointments:
        label = f"{a['patient_name']} — {a['service_name']} — {_fmt_date(a['date'], a['start_time'])}"
        b.button(text=label, callback_data=f"adm:view:{a['id']}")
    b.button(text="⬅️ Назад", callback_data="adm:menu")
    b.adjust(1)

    await callback.message.edit_text("Подтверждённые записи:", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:complete:"))
async def ask_amount_paid(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split(":")[2])
    await state.update_data(appointment_id=appointment_id)
    await state.set_state(AdminStates.entering_amount_paid)

    await callback.message.edit_text(
        "Введите фактическую сумму оплаты (в сум), например: 350000"
    )
    await callback.answer()


@router.message(AdminStates.entering_amount_paid)
async def receive_amount_paid(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip().replace(" ", "").replace(",", "")
    if not text.isdigit():
        await message.answer("Введите сумму цифрами, например: 350000")
        return

    amount_paid = float(text)
    data = await state.get_data()
    appointment_id = data["appointment_id"]

    pool = get_pool()
    a = await get_appointment_full(pool, appointment_id)

    result = await complete_appointment_with_bonus(
        pool,
        appointment_id=appointment_id,
        patient_id=a["patient_pk"],
        doctor_id=a["doctor_id"],
        amount_paid=amount_paid,
        bonus_percent=a["bonus_percent"],
    )

    await state.clear()

    price_str = f"{int(amount_paid):,}".replace(",", " ")
    await message.answer(
        f"✅ Визит отмечен завершённым.\nНачислено бонусов: {result['bonuses_earned']}"
        + (f"\n🎁 Также сработала реферальная программа (+{result['referred_bonus']} пациенту, "
           f"+{result['referrer_bonus']} пригласившему)" if result["referral_applied"] else "")
    )

    total_bonus_text = result["bonuses_earned"]
    if result["referral_applied"]:
        total_bonus_text = f"{result['bonuses_earned']} + {result['referred_bonus']} за приглашение друга"

    await bot.send_message(
        a["patient_telegram_id"],
        f"Спасибо за визит! 🦷\n\n"
        f"💰 Оплачено: {price_str} сум\n"
        f"🎁 Начислено бонусов: {total_bonus_text}\n\n"
        f"Проверить баланс можно в разделе «Мой уровень».",
    )

    if result["referral_applied"] and result["referrer_telegram_id"]:
        await bot.send_message(
            result["referrer_telegram_id"],
            f"🎉 Ваш друг посетил клинику впервые!\n"
            f"Вам начислено {result['referrer_bonus']} бонусов за приглашение.",
        )

    # проверяем достижения — и у самого пациента, и у того, кто его пригласил (если применимо)
    new_achievements = await check_and_award_achievements(pool, a["patient_pk"])
    for ach in new_achievements:
        await bot.send_message(
            a["patient_telegram_id"],
            f"🏆 Новое достижение: {ach['icon']} «{ach['name']}»!\n{ach['description']}",
        )

    if result["referral_applied"] and result["referrer_telegram_id"]:
        referrer_id_row = await pool.fetchrow(
            "SELECT id FROM patients WHERE telegram_id = $1", result["referrer_telegram_id"]
        )
        if referrer_id_row:
            referrer_new_achievements = await check_and_award_achievements(pool, referrer_id_row["id"])
            for ach in referrer_new_achievements:
                await bot.send_message(
                    result["referrer_telegram_id"],
                    f"🏆 Новое достижение: {ach['icon']} «{ach['name']}»!\n{ach['description']}",
                )
