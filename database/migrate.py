"""
Автоматически применяет .sql-файлы из migrations/ при каждом старте приложения.

Как это работает:
- В БД создаётся служебная таблица schema_migrations — список уже применённых файлов
- При старте бот смотрит на файлы вида 001_*.sql, 002_*.sql, ... (с числовым префиксом)
- Каждый файл, которого ещё нет в schema_migrations, применяется один раз и запоминается
- Повторные деплои НЕ переприменяют старые миграции — безопасно перезапускать сколько угодно

Файлы БЕЗ числового префикса (например seed_test_data.sql, если такой останется)
автоматически игнорируются — так делаются "разовые" миграции, которые применяются осознанно.
"""

import glob
import os
import logging
import asyncpg

logger = logging.getLogger(__name__)


async def apply_migrations(pool: asyncpg.Pool, migrations_dir: str = "migrations") -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename    TEXT PRIMARY KEY,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        applied = {r["filename"] for r in await conn.fetch("SELECT filename FROM schema_migrations")}

    pattern = os.path.join(migrations_dir, "[0-9]*.sql")
    files = sorted(glob.glob(pattern))

    if not files:
        logger.warning(f"Не найдено файлов миграций по пути {pattern}")
        return

    for filepath in files:
        filename = os.path.basename(filepath)
        if filename in applied:
            continue

        logger.info(f"Применяю миграцию: {filename}")
        with open(filepath, "r", encoding="utf-8") as f:
            sql = f.read()

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)", filename
                )

        logger.info(f"Миграция применена: {filename}")

    logger.info("Все миграции актуальны")
