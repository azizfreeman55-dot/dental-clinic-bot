from aiohttp import web
from datetime import date as date_cls

from database.pool import get_pool
from database.queries.admin import (
    is_admin, get_admin_stats, get_appointments_by_status, get_appointments_for_date,
    get_appointment_full, complete_appointment_with_bonus,
    get_pending_redemptions, mark_redemption_used,
)
from database.queries.appointments import confirm_appointment, cancel_appointment, propose_reschedule, get_free_slots
from database.queries.doctors import get_available_dates, shift_label
from database.queries.achievements import check_and_award_achievements
from database.queries.missions import check_and_award_missions

routes = web.RouteTableDef()

MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


async def _check_admin(request: web.Request):
    """Возвращает pool, если пользователь админ, иначе None — вызывающий код должен вернуть 403."""
    pool = get_pool()
    if not await is_admin(pool, request["telegram_id"]):
        return None
    return pool


def _fmt_dt(d, t):
    return f"{d.day} {MONTHS_RU[d.month - 1]} в {t.strftime('%H:%M')}"


# ---------- Статистика ----------

@routes.get("/api/admin/stats")
async def admin_stats(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    stats = await get_admin_stats(pool)
    return web.json_response({
        "pending_count": stats["pending_count"],
        "confirmed_count": stats["confirmed_count"],
        "awaiting_reschedule_count": stats["awaiting_reschedule_count"],
        "completed_today": stats["completed_today"],
        "completed_this_month": stats["completed_this_month"],
        "revenue_this_month": float(stats["revenue_this_month"]),
        "total_patients": stats["total_patients"],
        "new_patients_today": stats["new_patients_today"],
    })


# ---------- Списки заявок по статусу ----------

@routes.get("/api/admin/appointments")
async def admin_appointments_list(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    status = request.query.get("status", "pending")
    appointments = await get_appointments_by_status(pool, status)

    return web.json_response([
        {
            "id": a["id"],
            "status": a["status"],
            "patient_name": a["patient_name"],
            "phone": a["phone"],
            "doctor_name": a["doctor_name"],
            "service_name": a["service_name"],
            "price": float(a["price"]),
            "date": a["date"].isoformat(),
            "start_time": a["start_time"].strftime("%H:%M"),
            "formatted": _fmt_dt(a["date"], a["start_time"]),
        }
        for a in appointments
    ])


# ---------- Детали одной заявки ----------

@routes.get("/api/admin/appointments/{id}")
async def admin_appointment_detail(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    appointment_id = int(request.match_info["id"])
    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        return web.json_response({"error": "not_found"}, status=404)

    return web.json_response({
        "id": a["id"],
        "status": a["status"],
        "patient_name": a["patient_name"],
        "phone": a["phone"],
        "level_name": a["level_name"],
        "bonus_percent": float(a["bonus_percent"]),
        "bonus_balance": a["bonus_balance"],
        "completed_visits_count": a["completed_visits_count"],
        "referral_status": a["referral_status"],
        "doctor_name": a["doctor_name"],
        "doctor_specialization": a["doctor_specialization"],
        "doctor_shift": shift_label(a["doctor_shift_start"]),
        "service_name": a["service_name"],
        "service_description": a["service_description"],
        "price": float(a["price"]),
        "date": a["date"].isoformat(),
        "start_time": a["start_time"].strftime("%H:%M"),
        "formatted": _fmt_dt(a["date"], a["start_time"]),
        "created_at": a["created_at"].isoformat(),
    })


# ---------- Действия: подтвердить / отклонить / завершить визит ----------

@routes.post("/api/admin/appointments/{id}/confirm")
async def admin_confirm(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    appointment_id = int(request.match_info["id"])
    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        return web.json_response({"error": "not_found"}, status=404)

    await confirm_appointment(pool, appointment_id)

    bot = request.app["bot"]
    await bot.send_message(
        a["patient_telegram_id"],
        f"✅ Ваша запись подтверждена!\n\n👨‍⚕️ {a['doctor_name']}\n📅 {_fmt_dt(a['date'], a['start_time'])}\n\nЖдём вас в клинике!",
    )

    return web.json_response({"ok": True})


@routes.post("/api/admin/appointments/{id}/decline")
async def admin_decline(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    appointment_id = int(request.match_info["id"])
    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        return web.json_response({"error": "not_found"}, status=404)

    await cancel_appointment(pool, appointment_id, by_admin=True)

    bot = request.app["bot"]
    await bot.send_message(
        a["patient_telegram_id"],
        f"К сожалению, ваша запись на {_fmt_dt(a['date'], a['start_time'])} отклонена администратором. "
        f"Пожалуйста, выберите другое время в личном кабинете.",
    )

    return web.json_response({"ok": True})


# ---------- Перенос времени: даты / слоты / отправка предложения ----------

@routes.get("/api/admin/appointments/{id}/reschedule_dates")
async def admin_reschedule_dates(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    appointment_id = int(request.match_info["id"])
    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        return web.json_response({"error": "not_found"}, status=404)

    dates = await get_available_dates(pool, a["doctor_id"])
    return web.json_response([d.isoformat() for d in dates])


@routes.get("/api/admin/appointments/{id}/reschedule_slots")
async def admin_reschedule_slots(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    appointment_id = int(request.match_info["id"])
    date_str = request.query.get("date")
    if not date_str:
        return web.json_response({"error": "date обязателен"}, status=400)

    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        return web.json_response({"error": "not_found"}, status=404)

    slots = await get_free_slots(pool, a["doctor_id"], date_cls.fromisoformat(date_str))
    return web.json_response([
        {"id": s["id"], "start_time": s["start_time"].strftime("%H:%M")}
        for s in slots
    ])


@routes.post("/api/admin/appointments/{id}/reschedule")
async def admin_reschedule(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    appointment_id = int(request.match_info["id"])
    body = await request.json()
    new_slot_id = body.get("slot_id")
    if not new_slot_id:
        return web.json_response({"error": "slot_id обязателен"}, status=400)

    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        return web.json_response({"error": "not_found"}, status=404)

    new_appointment_id = await propose_reschedule(
        pool,
        old_appointment_id=appointment_id,
        patient_id=a["patient_pk"],
        doctor_id=a["doctor_id"],
        service_id=a["service_id"],
        new_slot_id=new_slot_id,
    )

    if new_appointment_id is None:
        return web.json_response({"error": "slot_taken", "message": "Этот слот уже заняли"}, status=409)

    new_a = await get_appointment_full(pool, new_appointment_id)

    bot = request.app["bot"]
    await bot.send_message(
        new_a["patient_telegram_id"],
        f"К сожалению, ваше время на {_fmt_dt(a['date'], a['start_time'])} было занято.\n\n"
        f"Но у нас есть свободное время: <b>{_fmt_dt(new_a['date'], new_a['start_time'])}</b> "
        f"у врача {new_a['doctor_name']} ({new_a['service_name']}).\n\n"
        f"Устроит вас такое время?",
        reply_markup=_reschedule_inline_kb(new_appointment_id),
    )

    return web.json_response({"ok": True, "new_appointment_id": new_appointment_id})


def _reschedule_inline_kb(new_appointment_id: int):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="✅ Подтверждаю", callback_data=f"pt:resched_yes:{new_appointment_id}")
    b.button(text="❌ Не подходит, отменить", callback_data=f"pt:resched_no:{new_appointment_id}")
    b.adjust(1)
    return b.as_markup()


@routes.post("/api/admin/appointments/{id}/complete")
async def admin_complete(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    appointment_id = int(request.match_info["id"])
    body = await request.json()
    amount_paid = body.get("amount_paid")

    if amount_paid is None:
        return web.json_response({"error": "amount_paid обязателен"}, status=400)

    a = await get_appointment_full(pool, appointment_id)
    if a is None:
        return web.json_response({"error": "not_found"}, status=404)

    result = await complete_appointment_with_bonus(
        pool,
        appointment_id=appointment_id,
        patient_id=a["patient_pk"],
        doctor_id=a["doctor_id"],
        amount_paid=float(amount_paid),
        bonus_percent=a["bonus_percent"],
    )

    bot = request.app["bot"]
    price_str = f"{int(float(amount_paid)):,}".replace(",", " ")
    total_bonus_text = result["bonuses_earned"]
    if result["referral_applied"]:
        total_bonus_text = f"{result['bonuses_earned']} + {result['referred_bonus']} за приглашение друга"

    await bot.send_message(
        a["patient_telegram_id"],
        f"Спасибо за визит! 🦷\n\n💰 Оплачено: {price_str} сум\n🎁 Начислено бонусов: {total_bonus_text}",
    )

    if result["referral_applied"] and result["referrer_telegram_id"]:
        await bot.send_message(
            result["referrer_telegram_id"],
            f"🎉 Ваш друг посетил клинику впервые!\nВам начислено {result['referrer_bonus']} бонусов за приглашение.",
        )

    new_achievements = await check_and_award_achievements(pool, a["patient_pk"])
    for ach in new_achievements:
        await bot.send_message(
            a["patient_telegram_id"],
            f"🏆 Новое достижение: {ach['icon']} «{ach['name']}»!\n{ach['description']}",
        )

    if result["referral_applied"] and result["referrer_telegram_id"]:
        referrer_row = await pool.fetchrow(
            "SELECT id FROM patients WHERE telegram_id = $1", result["referrer_telegram_id"]
        )
        if referrer_row:
            referrer_new_achievements = await check_and_award_achievements(pool, referrer_row["id"])
            for ach in referrer_new_achievements:
                await bot.send_message(
                    result["referrer_telegram_id"],
                    f"🏆 Новое достижение: {ach['icon']} «{ach['name']}»!\n{ach['description']}",
                )

    new_missions = await check_and_award_missions(pool, a["patient_pk"])
    for mis in new_missions:
        await bot.send_message(
            a["patient_telegram_id"],
            f"🎯 Миссия выполнена: «{mis['name']}»!\nНачислено {mis['reward_bonus']} бонусов.",
        )

    if result["referral_applied"] and result["referrer_telegram_id"]:
        referrer_row_for_missions = await pool.fetchrow(
            "SELECT id FROM patients WHERE telegram_id = $1", result["referrer_telegram_id"]
        )
        if referrer_row_for_missions:
            referrer_new_missions = await check_and_award_missions(pool, referrer_row_for_missions["id"])
            for mis in referrer_new_missions:
                await bot.send_message(
                    result["referrer_telegram_id"],
                    f"🎯 Миссия выполнена: «{mis['name']}»!\nНачислено {mis['reward_bonus']} бонусов.",
                )

    return web.json_response({"ok": True, **result})


# ---------- Календарь по дате ----------

@routes.get("/api/admin/calendar")
async def admin_calendar(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    date_str = request.query.get("date")
    target_date = date_cls.fromisoformat(date_str) if date_str else date_cls.today()

    appointments = await get_appointments_for_date(pool, target_date)

    return web.json_response([
        {
            "id": a["id"],
            "status": a["status"],
            "patient_name": a["patient_name"],
            "phone": a["phone"],
            "doctor_name": a["doctor_name"],
            "service_name": a["service_name"],
            "price": float(a["price"]),
            "start_time": a["start_time"].strftime("%H:%M"),
        }
        for a in appointments
    ])


# ---------- Погашения подарков ----------

@routes.get("/api/admin/redemptions")
async def admin_redemptions_list(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    redemptions = await get_pending_redemptions(pool)
    return web.json_response([
        {
            "id": r["id"],
            "patient_name": r["patient_name"],
            "phone": r["phone"],
            "gift_name": r["gift_name"],
            "cost_bonuses": r["cost_bonuses"],
            "redeemed_at": r["redeemed_at"].isoformat(),
        }
        for r in redemptions
    ])


@routes.post("/api/admin/redemptions/{id}/use")
async def admin_mark_redemption_used(request: web.Request):
    pool = await _check_admin(request)
    if pool is None:
        return web.json_response({"error": "forbidden"}, status=403)

    redemption_id = int(request.match_info["id"])
    ok = await mark_redemption_used(pool, redemption_id)

    if not ok:
        return web.json_response({"error": "not_found_or_already_used"}, status=404)

    return web.json_response({"ok": True})
