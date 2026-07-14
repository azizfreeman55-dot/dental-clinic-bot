# Dental Clinic Bot

Telegram-бот для стоматологии: онлайн-запись с реальным календарём, программа лояльности, Mini App.

## Статус разработки

Сделано:
- [x] Миграция БД: пациенты, врачи, услуги, расписание, слоты, записи, бонусы, уровни
- [x] `database/pool.py` — общий пул asyncpg
- [x] `database/queries/appointments.py` — race-safe бронирование слотов
- [x] `services/slot_generator.py` — генерация слотов из шаблона расписания (APScheduler)

Дальше:
- [ ] `bot.py` — каркас бота + webhook + aiohttp
- [ ] FSM записи (услуга → врач → календарь → слот)
- [ ] Mini App (React) — записи, бонусы, подарки, колесо
- [ ] Бонусы и уровни в интерфейсе
- [ ] Рефералка, подарки, геймификация

## Установка

```bash
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
```

Скопируй `.env.example` в `.env` и заполни `BOT_TOKEN`, `DATABASE_URL`.

## Применение миграции

```bash
psql "$DATABASE_URL" -f migrations/001_init.sql
```

## Структура

```
dental_bot/
├── migrations/          # SQL-миграции, применяются по порядку (001, 002, ...)
├── database/
│   ├── pool.py          # asyncpg pool, общий для бота и API
│   └── queries/         # SQL-запросы, разбитые по доменам
├── services/             # бизнес-логика: генерация слотов, напоминания, бонусы
├── bot_handlers/          # хэндлеры aiogram (появится дальше)
├── api/                   # REST для Mini App (появится дальше)
└── webapp/                # React Mini App (появится дальше)
```
