from aiohttp import web

from database.pool import get_pool
from database.queries.patients import get_or_create_patient
from database.queries.achievements import get_patient_achievements_status

routes = web.RouteTableDef()


@routes.get("/api/achievements")
async def list_achievements(request: web.Request):
    pool = get_pool()
    patient, _ = await get_or_create_patient(
        pool,
        telegram_id=request["telegram_id"],
        full_name=request["telegram_user"].get("first_name", "Пациент"),
    )

    achievements = await get_patient_achievements_status(pool, patient["id"])

    return web.json_response([
        {
            "id": a["id"],
            "code": a["code"],
            "name": a["name"],
            "description": a["description"],
            "icon": a["icon"],
            "earned": a["earned_at"] is not None,
            "earned_at": a["earned_at"].isoformat() if a["earned_at"] else None,
        }
        for a in achievements
    ])
