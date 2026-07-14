from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.pool import get_pool
from database.queries.patients import get_or_create_patient
import config

router = Router(name="start")


def main_menu_kb():
    builder = InlineKeyboardBuilder()
    if config.MINI_APP_URL:
        builder.button(text="📱 Личный кабинет", web_app=WebAppInfo(url=config.MINI_APP_URL))
    builder.adjust(1)
    return builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    pool = get_pool()

    referrer_telegram_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            referrer_telegram_id = int(command.args.removeprefix("ref_"))
        except ValueError:
            pass

    patient, created = await get_or_create_patient(
        pool,
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        referrer_telegram_id=referrer_telegram_id,
    )

    if created:
        greeting = (
            f"Здравствуйте, {message.from_user.first_name}! 👋\n\n"
            "Добро пожаловать в Стоматологию Жемчужина — вашу личную стоматологию.\n"
            "Здесь вы можете записаться на приём, копить бонусы и получать подарки."
        )
    else:
        greeting = f"С возвращением, {message.from_user.first_name}! 👋"

    await message.answer(greeting, reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:back")
async def back_to_menu(callback):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()
