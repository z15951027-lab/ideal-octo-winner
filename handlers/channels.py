from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import db
from config import DEFAULT_SUB_PRICE
from keyboards import main_menu, channel_manage_keyboard, confirm_delete_keyboard, cancel_keyboard

router = Router()


class AddChannel(StatesGroup):
    waiting_for_channel = State()


def _extract_identifier(message: Message) -> str | None:
    """Достаёт username канала из текста или из пересланного сообщения."""
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        chat = message.forward_from_chat
        return chat.username and f"@{chat.username}" or str(chat.id)
    if message.text:
        text = message.text.strip()
        if text.startswith("https://t.me/"):
            text = "@" + text.split("https://t.me/")[1].split("/")[0]
        if not text.startswith("@"):
            text = "@" + text
        return text
    return None


@router.message(Command("addchannel"))
@router.message(F.text == "➕ Добавить канал")
async def cmd_add_channel(message: Message, state: FSMContext):
    await state.set_state(AddChannel.waiting_for_channel)
    await message.answer(
        "Пришли мне @username своего канала или перешли любое сообщение из него.\n\n"
        "⚠️ Перед этим добавь меня в канал как <b>администратора</b> "
        "(достаточно прав на приглашение пользователей) — иначе я не смогу проверять подписки.\n\n"
        "Для отмены нажми «❌ Отмена».",
        reply_markup=cancel_keyboard(),
    )


@router.message(F.text == "❌ Отмена", StateFilter(AddChannel.waiting_for_channel))
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Нечего отменять.", reply_markup=main_menu())
        return
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu())


@router.message(StateFilter(AddChannel.waiting_for_channel))
async def process_channel(message: Message, state: FSMContext, bot: Bot):
    identifier = _extract_identifier(message)
    if not identifier:
        await message.answer("Не смог распознать канал. Пришли @username или перешли пост из канала.")
        return

    try:
        chat = await bot.get_chat(identifier)
    except Exception:
        await message.answer(
            "Не могу найти такой канал. Проверь username и то, что канал публичный, "
            "либо перешли сообщение из него."
        )
        return

    if chat.type != "channel":
        await message.answer("Это не канал. Пришли ссылку/username именно канала.")
        return

    try:
        bot_member = await bot.get_chat_member(chat.id, bot.id)
    except Exception:
        await message.answer("Не могу получить информацию о себе в этом канале. Добавь меня в администраторы.")
        return

    if bot_member.status not in ("administrator", "creator"):
        await message.answer(
            "Я не администратор этого канала. Добавь меня в администраторы и попробуй снова."
        )
        return

    try:
        user_member = await bot.get_chat_member(chat.id, message.from_user.id)
    except Exception:
        await message.answer("Не могу проверить твои права в канале. Попробуй ещё раз.")
        return

    if user_member.status not in ("administrator", "creator"):
        await message.answer("Добавлять канал может только его администратор или владелец.")
        return

    if await db.channel_exists_for_owner(message.from_user.id, chat.id):
        await message.answer("Этот канал уже добавлен тобой в бота.", reply_markup=main_menu())
        await state.clear()
        return

    await db.add_channel(
        owner_id=message.from_user.id,
        chat_id=chat.id,
        username=chat.username,
        title=chat.title,
        price=DEFAULT_SUB_PRICE,
    )
    await state.clear()
    await message.answer(
        f"Канал «{chat.title}» добавлен ✅\n\n"
        f"Он появится в заданиях у других пользователей, пока на твоём балансе хватает баллов "
        f"({DEFAULT_SUB_PRICE:.1f} балл за одного подписчика).",
        reply_markup=main_menu(),
    )


@router.message(Command("mychannels"))
@router.message(F.text == "📢 Мои каналы")
async def cmd_my_channels(message: Message):
    channels = await db.get_user_channels(message.from_user.id)
    if not channels:
        await message.answer(
            "У тебя пока нет добавленных каналов. Нажми «➕ Добавить канал».",
            reply_markup=main_menu(),
        )
        return

    await message.answer(f"Твои каналы ({len(channels)}):", reply_markup=main_menu())
    for ch in channels:
        confirmed = await db.count_confirmed_subs(ch["id"])
        status = "🟢 активен" if ch["active"] else "⏸ на паузе"
        await message.answer(
            f"<b>{ch['title']}</b>\n"
            f"Статус: {status}\n"
            f"Цена за подписчика: {ch['price']:.1f} балл\n"
            f"Получено подписчиков через бота: {confirmed}",
            reply_markup=channel_manage_keyboard(ch["id"], bool(ch["active"])),
        )


@router.callback_query(F.data.startswith("pause:"))
async def cb_pause(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    channel = await db.get_channel(channel_id)
    if not channel or channel["owner_id"] != callback.from_user.id:
        await callback.answer("Канал не найден.", show_alert=True)
        return
    await db.set_channel_active(channel_id, False)
    await callback.message.edit_reply_markup(reply_markup=channel_manage_keyboard(channel_id, False))
    await callback.answer("Канал поставлен на паузу.")


@router.callback_query(F.data.startswith("resume:"))
async def cb_resume(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    channel = await db.get_channel(channel_id)
    if not channel or channel["owner_id"] != callback.from_user.id:
        await callback.answer("Канал не найден.", show_alert=True)
        return
    await db.set_channel_active(channel_id, True)
    await callback.message.edit_reply_markup(reply_markup=channel_manage_keyboard(channel_id, True))
    await callback.answer("Канал снова активен.")


@router.callback_query(F.data.startswith("delete:"))
async def cb_delete_ask(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    channel = await db.get_channel(channel_id)
    if not channel or channel["owner_id"] != callback.from_user.id:
        await callback.answer("Канал не найден.", show_alert=True)
        return
    await callback.message.answer(
        f"Точно удалить канал «{channel['title']}» из бота?",
        reply_markup=confirm_delete_keyboard(channel_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
async def cb_delete_confirm(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    channel = await db.get_channel(channel_id)
    if not channel or channel["owner_id"] != callback.from_user.id:
        await callback.answer("Канал не найден.", show_alert=True)
        return
    await db.delete_channel(channel_id)
    await callback.message.edit_text(f"Канал «{channel['title']}» удалён из бота.")
    await callback.answer()


@router.callback_query(F.data.startswith("delete_cancel:"))
async def cb_delete_cancel(callback: CallbackQuery):
    await callback.message.edit_text("Удаление отменено.")
    await callback.answer()
