from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.pool import get_pool
from database.queries.patients import get_patient_by_telegram_id
from database.queries.referrals import get_referral_stats, REFERRER_BONUS_DEFAULT, REFERRED_BONUS_DEFAULT

router = Router(name="referral")


def back_kb():
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ В меню", callback_data="menu:back")
    return b.as_markup()


@router.callback_query(F.data == "menu:referral")
async def show_referral(callback: CallbackQuery, bot: Bot):
    pool = get_pool()
    patient = await get_patient_by_telegram_id(pool, callback.from_user.id)

    if patient is None:
        await callback.answer("Сначала нажмите /start", show_alert=True)
        return

    stats = await get_referral_stats(pool, patient["id"])
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"

    referrer_bonus_str = f"{REFERRER_BONUS_DEFAULT:,}".replace(",", " ")
    referred_bonus_str = f"{REFERRED_BONUS_DEFAULT:,}".replace(",", " ")

    text = (
        "👥 Приглашайте друзей и получайте бонусы!\n\n"
        f"Друг получает: {referred_bonus_str} бонусов на первый визит\n"
        f"Вы получаете: {referrer_bonus_str} бонусов, когда друг придёт в клинику\n\n"
        f"🔗 Ваша ссылка:\n{link}\n\n"
        f"Уже пригашено и получили бонус: {stats['rewarded_count']}\n"
        f"Ждут первого визита: {stats['pending_count']}\n"
        f"Заработано на рефералке: {stats['total_earned']} бонусов"
    )

    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()
