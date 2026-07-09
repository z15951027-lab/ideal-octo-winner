from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ---------- Главное меню (обычные кнопки) ----------

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Задание"), KeyboardButton(text="💰 Баланс")],
            [KeyboardButton(text="➕ Добавить канал"), KeyboardButton(text="📢 Мои каналы")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


# ---------- Инлайн-кнопки для задания ----------

def task_keyboard(channel_id: int, invite_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть канал", url=invite_url)],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data=f"check:{channel_id}")],
            [InlineKeyboardButton(text="⏭ Другое задание", callback_data="skip_task")],
        ]
    )


# ---------- Инлайн-кнопки для управления своим каналом ----------

def channel_manage_keyboard(channel_id: int, active: bool) -> InlineKeyboardMarkup:
    toggle_text = "⏸ Поставить на паузу" if active else "▶️ Возобновить"
    toggle_action = "pause" if active else "resume"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data=f"{toggle_action}:{channel_id}")],
            [InlineKeyboardButton(text="🗑 Удалить канал", callback_data=f"delete:{channel_id}")],
        ]
    )


def confirm_delete_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm:{channel_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"delete_cancel:{channel_id}"),
            ]
        ]
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
