from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.pool import get_pool
from database.queries.patients import get_patient_by_telegram_id, get_patient_level_info

router = Router(name="profile")


def back_kb():
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ В меню", callback_data="menu:back")
    return b.as_markup()


def fmt_money(n) -> str:
    return f"{int(n):,}".replace(",", " ")


@router.callback_query(F.data == "menu:level")
async def show_level(callback: CallbackQuery):
    pool = get_pool()
    patient = await get_patient_by_telegram_id(pool, callback.from_user.id)

    if patient is None:
        await callback.answer("Сначала нажмите /start", show_alert=True)
        return

    info = await get_patient_level_info(pool, patient["id"])

    text = (
        f"⭐ Ваш уровень: {info['level_name']}\n\n"
        f"💰 Бонусный баланс: {fmt_money(info['bonus_balance'])}\n"
        f"📈 Накоплено за всё время: {fmt_money(info['lifetime_bonus_earned'])}\n"
        f"🎁 Начисление с визита: {info['bonus_percent']}%\n"
    )

    if info["next_level_threshold"] is not None:
        remaining = max(0, info["next_level_threshold"] - info["lifetime_bonus_earned"])
        text += f"\nДо следующего уровня: {fmt_money(remaining)} бонусов"
    else:
        text += "\nЭто максимальный уровень 🏆"

    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()


@router.callback_query(F.data == "menu:bonuses")
async def show_bonuses_stub(callback: CallbackQuery):
    pool = get_pool()
    patient = await get_patient_by_telegram_id(pool, callback.from_user.id)

    if patient is None:
        await callback.answer("Сначала нажмите /start", show_alert=True)
        return

    text = (
        f"🎁 Ваш бонусный баланс: {fmt_money(patient['bonus_balance'])}\n\n"
        f"Каталог подарков и услуг за бонусы скоро появится здесь."
    )
    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()
