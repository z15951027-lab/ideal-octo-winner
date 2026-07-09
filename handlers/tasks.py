from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

import db
from config import SUB_REWARD, RECHECK_HOURS
from keyboards import main_menu, task_keyboard

router = Router()


async def _send_task(target, user_id: int, bot: Bot):
    channel = await db.get_random_task(user_id)
    if not channel:
        await target.answer(
            "Сейчас нет доступных заданий 🙁 Загляни чуть позже — "
            "новые каналы появляются, когда у их владельцев есть баллы на балансе.",
            reply_markup=main_menu(),
        )
        return

    if channel["username"]:
        url = f"https://t.me/{channel['username']}"
    else:
        # приватный канал без username — придётся давать инвайт-ссылку вручную (не реализовано)
        url = f"https://t.me/c/{str(channel['chat_id']).replace('-100', '')}"

    await target.answer(
        f"📋 <b>Задание</b>\n\n"
        f"Подпишись на канал «{channel['title']}», затем нажми «✅ Я подписался».\n\n"
        f"За это начислится <b>{SUB_REWARD:.1f}</b> балла (зачислятся окончательно через "
        f"{RECHECK_HOURS} ч., если не отпишешься раньше).",
        reply_markup=task_keyboard(channel["id"], url),
    )


@router.message(Command("task"))
@router.message(F.text == "📋 Задание")
async def cmd_task(message: Message, bot: Bot):
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    await _send_task(message, message.from_user.id, bot)


@router.callback_query(F.data == "skip_task")
async def cb_skip_task(callback: CallbackQuery, bot: Bot):
    await callback.message.delete()
    await _send_task(callback.message, callback.from_user.id, bot)
    await callback.answer()


@router.callback_query(F.data.startswith("check:"))
async def cb_check_subscription(callback: CallbackQuery, bot: Bot):
    channel_id = int(callback.data.split(":")[1])
    channel = await db.get_channel(channel_id)

    if not channel or not channel["active"]:
        await callback.answer("Это задание больше недоступно.", show_alert=True)
        return

    if channel["owner_id"] == callback.from_user.id:
        await callback.answer("Это твой собственный канал 🙂", show_alert=True)
        return

    owner = await db.get_user(channel["owner_id"])
    if not owner or owner["balance"] < channel["price"]:
        await callback.answer("У владельца канала закончились баллы, задание больше не активно.", show_alert=True)
        return

    try:
        member = await bot.get_chat_member(channel["chat_id"], callback.from_user.id)
    except Exception:
        await callback.answer("Не получилось проверить подписку. Попробуй ещё раз чуть позже.", show_alert=True)
        return

    if member.status not in ("member", "administrator", "creator"):
        await callback.answer("Не вижу твою подписку. Подпишись на канал и нажми кнопку снова.", show_alert=True)
        return

    try:
        await db.create_frozen_subscription(callback.from_user.id, channel, SUB_REWARD)
    except Exception:
        # скорее всего сработал UNIQUE(user_id, channel_id) — задание уже выполнялось
        await callback.answer("Ты уже выполнял это задание раньше.", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Подписка на «{channel['title']}» замечена!\n\n"
        f"Баллы ({SUB_REWARD:.1f}) сейчас заморожены и зачислятся на баланс через "
        f"{RECHECK_HOURS} ч., если ты не отпишешься от канала."
    )
    await callback.answer("Засчитано! Баллы заморожены до проверки.")
