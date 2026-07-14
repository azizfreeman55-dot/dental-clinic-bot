from aiohttp import web

from database.pool import get_pool
from database.queries.patients import get_or_create_patient
from database.queries.missions import get_patient_missions_status

routes = web.RouteTableDef()


@routes.get("/api/missions")
async def list_missions(request: web.Request):
    pool = get_pool()
    patient, _ = await get_or_create_patient(
        pool,
        telegram_id=request["telegram_id"],
        full_name=request["telegram_user"].get("first_name", "Пациент"),
    )

    missions = await get_patient_missions_status(pool, patient["id"])
    return web.json_response(missions)
