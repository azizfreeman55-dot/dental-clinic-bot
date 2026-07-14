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
from database.queries.appointments import confirm_appointment, cancel_appointment
from bot_handlers.admin.filters import IsAdmin
from states import AdminStates

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def _fmt_date(d, t):
    return f"{d.day} {MONTHS_RU[d.month - 1]} в {t.strftime('%H:%M')}"


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
        label = f"{a['patient_name']} — {_fmt_date(a['date'], a['start_time'])}"
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
    appointment_id = int(callback.data.split(":")[2])
    pool = get_pool()
    a = await get_appointment_full(pool, appointment_id)

    if a is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    price_str = f"{int(a['price']):,}".replace(",", " ")
    text = (
        f"📋 Заявка №{a['id']}\n\n"
        f"👤 Пациент: {a['patient_name']}\n"
        f"👨‍⚕️ Врач: {a['doctor_name']}\n"
        f"💉 Услуга: {a['service_name']} — {price_str} сум\n"
        f"📅 Время: {_fmt_date(a['date'], a['start_time'])}\n"
        f"Статус: {a['status']}"
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
        label = f"{a['patient_name']} — {_fmt_date(a['date'], a['start_time'])}"
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
