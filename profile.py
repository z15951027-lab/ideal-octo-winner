from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

import db
from keyboards import main_menu

router = Router()


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        user, _ = await db.get_or_create_user(message.from_user.id, message.from_user.username)

    channels_count = await db.count_user_channels(message.from_user.id)
    completed_tasks = await db.count_completed_tasks(message.from_user.id)

    joined = user["created_at"]
    try:
        joined = datetime.fromisoformat(joined).strftime("%d.%m.%Y")
    except Exception:
        pass

    username_line = f"@{message.from_user.username}" if message.from_user.username else "не указан"

    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"ID: <code>{message.from_user.id}</code>\n"
        f"Username: {username_line}\n"
        f"В боте с: {joined}\n\n"
        f"💰 Доступно баллов: <b>{user['balance']:.1f}</b>\n"
        f"🧊 Заморожено: <b>{user['frozen_balance']:.1f}</b>\n\n"
        f"📢 Каналов добавлено: <b>{channels_count}</b>\n"
        f"✅ Заданий выполнено: <b>{completed_tasks}</b>",
        reply_markup=main_menu(),
    )
