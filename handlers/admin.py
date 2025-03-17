from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.database import get_db, get_user_by_telegram_id, is_admin, add_admin
from sqlalchemy.orm import Session
from states.admin_states import AdminStates

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

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data="confirm_add_admin"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_add_admin")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@admin_router.message(Command("admin"))
async def admin_command(message: types.Message, db: Session):
    if not is_admin(db, message.from_user.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    
    await message.answer(
        "Панель управления администраторами",
        reply_markup=get_admin_keyboard()
    )

@admin_router.callback_query(lambda c: c.data == "add_admin")
async def process_add_admin(callback: types.CallbackQuery, state: FSMContext, db: Session):
    if not is_admin(db, callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.message.edit_text(
        "Пожалуйста, введите ID пользователя, которого хотите сделать администратором.\n"
        "ID можно получить, переслав сообщение от пользователя боту @getidsbot"
    )

@admin_router.message(AdminStates.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext, db: Session):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный ID пользователя (только цифры).")
        return
    
    user = get_user_by_telegram_id(db, user_id)
    if not user:
        await message.answer("❌ Пользователь с таким ID не найден в базе данных.")
        return
    
    if is_admin(db, user_id):
        await message.answer("❌ Этот пользователь уже является администратором.")
        return
    
    await state.update_data(user_id=user_id)
    await state.set_state(AdminStates.confirming_add_admin)
    
    await message.answer(
        f"Вы уверены, что хотите сделать администратором пользователя:\n"
        f"ID: {user_id}\n"
        f"Имя: {user.first_name} {user.last_name or ''}\n"
        f"Username: @{user.username or 'не указан'}",
        reply_markup=get_confirm_keyboard()
    )

@admin_router.callback_query(lambda c: c.data == "confirm_add_admin", AdminStates.confirming_add_admin)
async def process_confirm_add_admin(callback: types.CallbackQuery, state: FSMContext, db: Session):
    data = await state.get_data()
    user_id = data['user_id']
    
    user = add_admin(db, user_id)
    if user:
        await callback.message.edit_text(
            f"✅ Пользователь {user.first_name} {user.last_name or ''} "
            f"(@{user.username or 'не указан'}) успешно добавлен в администраторы."
        )
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при добавлении администратора."
        )
    
    await state.clear()

@admin_router.callback_query(lambda c: c.data == "cancel_add_admin", AdminStates.confirming_add_admin)
async def process_cancel_add_admin(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Добавление администратора отменено.")
    await state.clear() 