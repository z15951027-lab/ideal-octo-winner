from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

import db
from config import START_BONUS, SUB_REWARD, RECHECK_HOURS
from keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user, created = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    if created:
        text = (
            f"Привет! 👋 Это бот для взаимных подписок.\n\n"
            f"Тебе начислено <b>{START_BONUS:.1f}</b> балла в подарок — их можно сразу "
            f"потратить на подписчиков для своего канала.\n\n"
            f"Как это работает:\n"
            f"1. Добавь свой канал через «➕ Добавить канал».\n"
            f"2. Выполняй «📋 Задание» — подписывайся на другие каналы, за это начисляются баллы.\n"
            f"3. Баллы списываются с владельцев тех каналов, на которые подписываются — "
            f"так на твой канал будут подписываться другие.\n\n"
            f"⚠️ Баллы за задание сначала «замораживаются» и зачисляются на баланс только через "
            f"{RECHECK_HOURS} ч., если ты не отпишешься от канала."
        )
    else:
        text = "С возвращением! Выбирай действие в меню 👇"
    await message.answer(text, reply_markup=main_menu())


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "<b>Как устроен бот</b>\n\n"
        f"• За каждое выполненное задание (подписку на чужой канал) начисляется "
        f"<b>{SUB_REWARD:.1f}</b> балла.\n"
        f"• 1 балл = 1 подписчик на твоём канале.\n"
        f"• Баллы сначала замораживаются и зачисляются на баланс окончательно через "
        f"{RECHECK_HOURS} ч. — бот проверяет, что ты не отписался.\n"
        f"• Если отписаться раньше — баллы сгорают, а владельцу канала возвращаются его баллы.\n\n"
        "<b>Команды</b>\n"
        "/start — начать / открыть меню\n"
        "/profile — профиль и статистика\n"
        "/balance — показать баланс\n"
        "/addchannel — добавить канал\n"
        "/mychannels — мои каналы\n"
        "/task — получить задание\n"
        "/cancel — отменить текущее действие",
        reply_markup=main_menu(),
    )
