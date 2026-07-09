from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

import db
from keyboards import main_menu

router = Router()


@router.message(Command("balance"))
@router.message(F.text == "💰 Баланс")
async def cmd_balance(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        user, _ = await db.get_or_create_user(message.from_user.id, message.from_user.username)

    await message.answer(
        f"💰 <b>Твой баланс</b>\n\n"
        f"Доступно: <b>{user['balance']:.1f}</b> баллов\n"
        f"Заморожено (ожидает проверки): <b>{user['frozen_balance']:.1f}</b> баллов\n\n"
        f"1 балл = 1 подписчик на твоём канале.",
        reply_markup=main_menu(),
    )
