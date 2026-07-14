from aiohttp import web

from database.pool import get_pool
from database.queries.patients import get_or_create_patient
from database.queries.gifts import get_active_gifts, redeem_gift, get_patient_redemptions

routes = web.RouteTableDef()


@routes.get("/api/gifts")
async def list_gifts(request: web.Request):
    pool = get_pool()
    gifts = await get_active_gifts(pool)
    return web.json_response([
        {
            "id": g["id"],
            "name": g["name"],
            "description": g["description"],
            "cost_bonuses": g["cost_bonuses"],
            "category": g["category"],
            "image_url": g["image_url"],
        }
        for g in gifts
    ])


@routes.post("/api/gifts/{id}/redeem")
async def redeem(request: web.Request):
    pool = get_pool()
    telegram_id = request["telegram_id"]
    gift_id = int(request.match_info["id"])

    patient, _ = await get_or_create_patient(
        pool, telegram_id=telegram_id, full_name=request["telegram_user"].get("first_name", "Пациент")
    )

    redemption_id = await redeem_gift(pool, patient["id"], gift_id)

    if redemption_id is None:
        return web.json_response(
            {"error": "insufficient_balance", "message": "Недостаточно бонусов или подарок недоступен"},
            status=409,
        )

    return web.json_response({"redemption_id": redemption_id, "status": "pending"})


@routes.get("/api/gifts/my")
async def my_redemptions(request: web.Request):
    pool = get_pool()
    telegram_id = request["telegram_id"]

    patient, _ = await get_or_create_patient(
        pool, telegram_id=telegram_id, full_name=request["telegram_user"].get("first_name", "Пациент")
    )
    redemptions = await get_patient_redemptions(pool, patient["id"])

    return web.json_response([
        {
            "id": r["id"],
            "status": r["status"],
            "gift_name": r["gift_name"],
            "gift_description": r["gift_description"],
            "cost_bonuses": r["cost_bonuses"],
            "redeemed_at": r["redeemed_at"].isoformat(),
            "used_at": r["used_at"].isoformat() if r["used_at"] else None,
        }
        for r in redemptions
    ])
