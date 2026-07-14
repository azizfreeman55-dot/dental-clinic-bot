import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from database.pool import init_pool, close_pool, get_pool
from database.migrate import apply_migrations
from database.queries.admin import ensure_admin
from services.slot_generator import generate_slots_for_all_doctors, setup_scheduler_jobs
from services.reminders import send_reminders

from bot_handlers import start, booking, referral, profile, patient_actions
from bot_handlers.admin import appointments as admin_appointments
from api.middleware import telegram_auth_middleware
from api.routes import booking as api_booking
from api.routes import admin as api_admin
from api.routes import gifts as api_gifts
from api.routes import wheel as api_wheel
from api.routes import achievements as api_achievements
from api.routes import missions as api_missions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(referral.router)
    dp.include_router(profile.router)
    dp.include_router(patient_actions.router)
    dp.include_router(admin_appointments.router)
    return dp


async def on_startup(bot: Bot):
    pool = await init_pool(config.DATABASE_URL)

    await apply_migrations(pool)

    if config.ADMIN_TELEGRAM_ID:
        await ensure_admin(pool, int(config.ADMIN_TELEGRAM_ID))
        logger.info(f"Админ назначен: {config.ADMIN_TELEGRAM_ID}")

    # генерируем слоты сразу при старте, чтобы не ждать ночной джобы на первом деплое
    await generate_slots_for_all_doctors(pool)

    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    setup_scheduler_jobs(scheduler, pool)
    scheduler.add_job(
        send_reminders,
        "interval",
        minutes=15,
        args=[bot, pool],
        id="send_reminders",
        replace_existing=True,
    )
    scheduler.start()

    if config.WEBHOOK_URL:
        await bot.set_webhook(config.WEBHOOK_URL)
        logger.info(f"Webhook установлен: {config.WEBHOOK_URL}")

    logger.info("Бот запущен")


async def on_shutdown(bot: Bot):
    await close_pool()
    logger.info("Бот остановлен, пул соединений закрыт")


def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if config.WEBHOOK_BASE_URL:
        # ---------- Продакшн: webhook + aiohttp (нужен для Render и для будущего Mini App API) ----------
        app = web.Application(middlewares=[telegram_auth_middleware])
        app["bot"] = bot

        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=config.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        app.add_routes(api_booking.routes)
        app.add_routes(api_admin.routes)
        app.add_routes(api_gifts.routes)
        app.add_routes(api_wheel.routes)
        app.add_routes(api_achievements.routes)
        app.add_routes(api_missions.routes)

        # раздача собранного Mini App (webapp/dist после `npm run build`).
        # aiohttp.static НЕ отдаёт index.html автоматически для корня папки (в отличие от nginx),
        # поэтому ассеты и index.html регистрируем раздельно.
        app.router.add_static("/webapp/assets", path="webapp/dist/assets")

        async def serve_webapp_index(request):
            return web.FileResponse("webapp/dist/index.html")

        app.router.add_get("/webapp", serve_webapp_index)
        app.router.add_get("/webapp/", serve_webapp_index)

        web.run_app(app, host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 8080)))
    else:
        # ---------- Локальная разработка: polling, без webhook ----------
        logger.info("WEBHOOK_BASE_URL не задан — запуск в режиме polling (для локальной разработки)")
        asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
