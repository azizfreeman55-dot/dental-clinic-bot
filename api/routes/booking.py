from aiohttp import web
from datetime import date as date_cls
import json

from database.pool import get_pool
from database.queries.patients import get_or_create_patient, get_patient_level_info
from database.queries.doctors import get_active_services, get_doctors_for_service, get_available_dates
from database.queries.appointments import get_free_slots, book_slot
from database.queries.referrals import get_referral_stats, REFERRER_BONUS_DEFAULT, REFERRED_BONUS_DEFAULT
from services.notifications import notify_admins_new_appointment

routes = web.RouteTableDef()


# ---------- Профиль ----------

@routes.get("/api/me")
async def get_me(request: web.Request):
    pool = get_pool()
    telegram_id = request["telegram_id"]
    user = request["telegram_user"]

    patient, _ = await get_or_create_patient(
        pool, telegram_id=telegram_id, full_name=user.get("first_name", "Пациент")
    )
    level_info = await get_patient_level_info(pool, patient["id"])

    benefits_raw = level_info["benefits"]
    benefits = json.loads(benefits_raw) if isinstance(benefits_raw, str) else (benefits_raw or [])

    return web.json_response({
        "id": patient["id"],
        "full_name": patient["full_name"],
        "bonus_balance": patient["bonus_balance"],
        "level_name": level_info["level_name"],
        "bonus_percent": float(level_info["bonus_percent"]),
        "next_level_threshold": level_info["next_level_threshold"],
        "lifetime_bonus_earned": level_info["lifetime_bonus_earned"],
        "benefits": benefits,
    })


# ---------- Запись: справочники ----------

@routes.get("/api/services")
async def list_services(request: web.Request):
    pool = get_pool()
    services = await get_active_services(pool)
    return web.json_response([
        {"id": s["id"], "name": s["name"], "price": float(s["price"]), "duration_min": s["duration_min"]}
        for s in services
    ])


@routes.get("/api/doctors")
async def list_doctors(request: web.Request):
    from database.queries.doctors import shift_label

    service_id = request.query.get("service_id")
    if not service_id:
        return web.json_response({"error": "service_id обязателен"}, status=400)

    pool = get_pool()
    doctors = await get_doctors_for_service(pool, int(service_id))
    return web.json_response([
        {
            "id": d["id"],
            "full_name": d["full_name"],
            "specialization": d["specialization"],
            "photo_url": d["photo_url"],
            "shift": shift_label(d["shift_start"]),
        }
        for d in doctors
    ])


@routes.get("/api/dates")
async def list_dates(request: web.Request):
    doctor_id = request.query.get("doctor_id")
    if not doctor_id:
        return web.json_response({"error": "doctor_id обязателен"}, status=400)

    pool = get_pool()
    dates = await get_available_dates(pool, int(doctor_id))
    return web.json_response([d.isoformat() for d in dates])


@routes.get("/api/slots")
async def list_slots(request: web.Request):
    doctor_id = request.query.get("doctor_id")
    date_str = request.query.get("date")
    if not doctor_id or not date_str:
        return web.json_response({"error": "doctor_id и date обязательны"}, status=400)

    pool = get_pool()
    slots = await get_free_slots(pool, int(doctor_id), date_cls.fromisoformat(date_str))
    return web.json_response([
        {"id": s["id"], "start_time": s["start_time"].strftime("%H:%M"), "end_time": s["end_time"].strftime("%H:%M")}
        for s in slots
    ])


# ---------- Бронирование ----------

@routes.post("/api/book")
async def create_booking(request: web.Request):
    pool = get_pool()
    telegram_id = request["telegram_id"]
    body = await request.json()

    service_id = body.get("service_id")
    doctor_id = body.get("doctor_id")
    slot_id = body.get("slot_id")

    if not all([service_id, doctor_id, slot_id]):
        return web.json_response({"error": "service_id, doctor_id, slot_id обязательны"}, status=400)

    patient, _ = await get_or_create_patient(pool, telegram_id=telegram_id, full_name=request["telegram_user"].get("first_name", "Пациент"))

    appointment_id = await book_slot(
        pool, patient_id=patient["id"], doctor_id=doctor_id, service_id=service_id, slot_id=slot_id
    )

    if appointment_id is None:
        return web.json_response({"error": "slot_taken", "message": "Слот только что заняли, выберите другой"}, status=409)

    bot = request.app["bot"]
    await notify_admins_new_appointment(bot, pool, appointment_id)

    return web.json_response({"appointment_id": appointment_id, "status": "pending"})


# ---------- Рефералка ----------

@routes.get("/api/referral")
async def referral_info(request: web.Request):
    pool = get_pool()
    telegram_id = request["telegram_id"]

    patient, _ = await get_or_create_patient(pool, telegram_id=telegram_id, full_name=request["telegram_user"].get("first_name", "Пациент"))
    stats = await get_referral_stats(pool, patient["id"])

    bot = request.app["bot"]
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{telegram_id}"

    return web.json_response({
        "link": link,
        "rewarded_count": stats["rewarded_count"],
        "pending_count": stats["pending_count"],
        "total_earned": stats["total_earned"],
        "referrer_bonus_default": REFERRER_BONUS_DEFAULT,
        "referred_bonus_default": REFERRED_BONUS_DEFAULT,
    })
