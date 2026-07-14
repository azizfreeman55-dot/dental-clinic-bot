from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import date as date_cls

from database.pool import get_pool
from database.queries.doctors import (
    get_active_services, get_doctors_for_service, get_available_dates,
    get_service, get_doctor,
)
from database.queries.appointments import get_free_slots, book_slot
from database.queries.patients import get_patient_by_telegram_id
from services.notifications import notify_admins_new_appointment
from states import BookingStates
from keyboards.booking_kb import services_kb, doctors_kb, dates_kb, slots_kb, confirm_kb, WEEKDAYS_RU, MONTHS_RU

router = Router(name="booking")


# ---------- Старт записи ----------

@router.callback_query(F.data == "menu:book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    pool = get_pool()
    services = await get_active_services(pool)

    if not services:
        await callback.answer("Пока нет доступных услуг, зайдите позже", show_alert=True)
        return

    await state.set_state(BookingStates.choosing_service)
    await callback.message.edit_text(
        "Выберите услугу:", reply_markup=services_kb(services)
    )
    await callback.answer()


# ---------- Выбор врача ----------

@router.callback_query(BookingStates.choosing_service, F.data.startswith("svc:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    pool = get_pool()

    doctors = await get_doctors_for_service(pool, service_id)
    if not doctors:
        await callback.answer("К сожалению, для этой услуги пока нет доступных врачей", show_alert=True)
        return

    await state.update_data(service_id=service_id)
    await state.set_state(BookingStates.choosing_doctor)
    await callback.message.edit_text(
        "Выберите врача:", reply_markup=doctors_kb(doctors)
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_doctor, F.data == "back:service")
async def back_to_service(callback: CallbackQuery, state: FSMContext):
    await start_booking(callback, state)


# ---------- Выбор даты ----------

@router.callback_query(BookingStates.choosing_doctor, F.data.startswith("doc:"))
async def choose_doctor(callback: CallbackQuery, state: FSMContext):
    doctor_id = int(callback.data.split(":")[1])
    pool = get_pool()

    dates = await get_available_dates(pool, doctor_id)
    if not dates:
        await callback.answer("У этого врача нет свободных дат в ближайшие 2 недели", show_alert=True)
        return

    await state.update_data(doctor_id=doctor_id)
    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text(
        "Выберите дату:", reply_markup=dates_kb(dates)
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_date, F.data == "back:doctor")
async def back_to_doctor(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pool = get_pool()
    doctors = await get_doctors_for_service(pool, data["service_id"])
    await state.set_state(BookingStates.choosing_doctor)
    await callback.message.edit_text("Выберите врача:", reply_markup=doctors_kb(doctors))
    await callback.answer()


# ---------- Выбор слота ----------

@router.callback_query(BookingStates.choosing_date, F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    chosen_date = date_cls.fromisoformat(callback.data.split(":")[1])
    data = await state.get_data()
    pool = get_pool()

    slots = await get_free_slots(pool, data["doctor_id"], chosen_date)
    if not slots:
        await callback.answer("На эту дату слотов уже не осталось, выберите другую", show_alert=True)
        return

    await state.update_data(date=chosen_date.isoformat())
    await state.set_state(BookingStates.choosing_slot)
    await callback.message.edit_text(
        f"Свободное время на {chosen_date.day} {MONTHS_RU[chosen_date.month - 1]}:",
        reply_markup=slots_kb(slots),
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_slot, F.data == "back:date")
async def back_to_date(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pool = get_pool()
    dates = await get_available_dates(pool, data["doctor_id"])
    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text("Выберите дату:", reply_markup=dates_kb(dates))
    await callback.answer()


# ---------- Подтверждение ----------

@router.callback_query(BookingStates.choosing_slot, F.data.startswith("slot:"))
async def choose_slot(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    pool = get_pool()

    service = await get_service(pool, data["service_id"])
    doctor = await get_doctor(pool, data["doctor_id"])
    chosen_date = date_cls.fromisoformat(data["date"])

    await state.update_data(slot_id=slot_id)
    await state.set_state(BookingStates.confirming)

    price_str = f"{int(service['price']):,}".replace(",", " ")
    text = (
        f"Проверьте запись:\n\n"
        f"💉 Услуга: {service['name']}\n"
        f"👨‍⚕️ Врач: {doctor['full_name']}\n"
        f"📅 Дата: {chosen_date.day} {MONTHS_RU[chosen_date.month - 1]}, {WEEKDAYS_RU[chosen_date.weekday()]}\n"
        f"💰 Стоимость: {price_str} сум\n\n"
        f"После подтверждения запись перейдёт администратору на согласование."
    )
    await callback.message.edit_text(text, reply_markup=confirm_kb())
    await callback.answer()


@router.callback_query(BookingStates.confirming, F.data == "confirm:no")
async def cancel_confirmation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запись отменена. Чтобы начать заново — нажмите «Записаться на приём» в меню.")
    await callback.answer()


@router.callback_query(BookingStates.confirming, F.data == "confirm:yes")
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot):
    data = await state.get_data()
    pool = get_pool()

    patient = await get_patient_by_telegram_id(pool, callback.from_user.id)
    if patient is None:
        await callback.answer("Ошибка: пациент не найден, напишите /start", show_alert=True)
        await state.clear()
        return

    appointment_id = await book_slot(
        pool,
        patient_id=patient["id"],
        doctor_id=data["doctor_id"],
        service_id=data["service_id"],
        slot_id=data["slot_id"],
    )

    await state.clear()

    if appointment_id is None:
        await callback.message.edit_text(
            "К сожалению, этот слот только что заняли. Пожалуйста, начните запись заново — "
            "нажмите «Записаться на приём» в меню."
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Заявка на запись отправлена!\n\n"
        "Администратор клиники подтвердит её в ближайшее время, и вам придёт уведомление."
    )
    await callback.answer()

    await notify_admins_new_appointment(bot, pool, appointment_id)
