from aiohttp import web

import config
from api.auth import validate_init_data


@web.middleware
async def telegram_auth_middleware(request: web.Request, handler):
    if not request.path.startswith("/api/"):
        return await handler(request)

    init_data = request.headers.get("X-Telegram-Init-Data", "")
    validated = validate_init_data(init_data, config.BOT_TOKEN)

    if validated is None or not validated["user"]:
        return web.json_response({"error": "unauthorized"}, status=401)

    # кладём telegram_id в request — хэндлеры дальше используют его,
    # НИКОГДА не берут telegram_id из тела/параметров запроса (это и есть защита от подмены)
    request["telegram_id"] = validated["user"]["id"]
    request["telegram_user"] = validated["user"]

    return await handler(request)
