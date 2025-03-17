from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.database import get_db, get_user_by_telegram_id
from sqlalchemy.orm import Session

admin_router = Router()

def get_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="➕ Добавить админа", callback_data="add_admin"),
            InlineKeyboardButton(text="❌ Удалить админа", callback_data="remove_admin")
        ],
        [
            InlineKeyboardButton(text="📋 Список админов", callback_data="list_admins")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@admin_router.message(Command("admin"))
async def admin_command(message: types.Message, db: Session):
    user = get_user_by_telegram_id(db, message.from_user.id)
    if not user or not user.is_admin:
        await message.answer("У вас нет доступа к этой команде.")
        return
    
    await message.answer(
        "Панель управления администраторами",
        reply_markup=get_admin_keyboard()
    ) 