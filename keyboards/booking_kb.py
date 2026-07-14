from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def services_kb(services: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in services:
        price_str = f"{int(s['price']):,}".replace(",", " ")
        builder.button(
            text=f"{s['name']} — {price_str} сум",
            callback_data=f"svc:{s['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def doctors_kb(doctors: list) -> InlineKeyboardMarkup:
    from database.queries.doctors import shift_label
    builder = InlineKeyboardBuilder()
    for d in doctors:
        label = shift_label(d["shift_start"])
        text = f"{d['full_name']} — {label}" if label else d['full_name']
        builder.button(text=text, callback_data=f"doc:{d['id']}")
    builder.button(text="⬅️ Назад", callback_data="back:service")
    builder.adjust(1)
    return builder.as_markup()


def dates_kb(dates: list[date]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in dates:
        label = f"{WEEKDAYS_RU[d.weekday()]} {d.day} {MONTHS_RU[d.month - 1]}"
        builder.button(text=label, callback_data=f"date:{d.isoformat()}")
    builder.button(text="⬅️ Назад", callback_data="back:doctor")
    builder.adjust(3)
    return builder.as_markup()


def slots_kb(slots: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in slots:
        builder.button(text=s["start_time"].strftime("%H:%M"), callback_data=f"slot:{s['id']}")
    builder.button(text="⬅️ Назад", callback_data="back:date")
    builder.adjust(4)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data="confirm:yes")
    builder.button(text="❌ Отмена", callback_data="confirm:no")
    builder.adjust(1)
    return builder.as_markup()
