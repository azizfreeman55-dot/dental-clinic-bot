from aiohttp import web

from database.pool import get_pool
from database.queries.patients import get_or_create_patient
from database.queries.wheel import get_active_prizes, get_spins_available, spin_wheel

routes = web.RouteTableDef()


async def _get_patient(request: web.Request):
    pool = get_pool()
    patient, _ = await get_or_create_patient(
        pool,
        telegram_id=request["telegram_id"],
        full_name=request["telegram_user"].get("first_name", "Пациент"),
    )
    return pool, patient


@routes.get("/api/wheel/prizes")
async def wheel_prizes(request: web.Request):
    pool = get_pool()
    prizes = await get_active_prizes(pool)
    return web.json_response([
        {"id": p["id"], "name": p["name"], "bonus_amount": p["bonus_amount"], "color": p["color"]}
        for p in prizes
    ])


@routes.get("/api/wheel/status")
async def wheel_status(request: web.Request):
    pool, patient = await _get_patient(request)
    spins = await get_spins_available(pool, patient["id"])
    return web.json_response({"spins_available": spins})


@routes.post("/api/wheel/spin")
async def wheel_spin(request: web.Request):
    pool, patient = await _get_patient(request)
    result = await spin_wheel(pool, patient["id"])

    if result is None:
        return web.json_response({"error": "no_spins", "message": "Нет доступных вращений"}, status=409)

    return web.json_response(result)
