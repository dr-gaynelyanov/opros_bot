from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards.reply import get_contact_keyboard, get_admin_start_inline_keyboard, get_user_start_keyboard
from states.user_states import UserRegistration
from database.database import get_db, create_user, get_user_by_telegram_id, is_admin, get_poll_by_access_code, create_poll_response
import logging
import re
from sqlalchemy.orm import Session

common_router = Router()

@common_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: Session):
    user = get_user_by_telegram_id(db, message.from_user.id)
    
    if is_admin(db, message.from_user.id):
        await message.answer(
            f"Добро пожаловать, администратор {user.first_name}! 👋\n",
            reply_markup=get_admin_start_inline_keyboard()
        )
        return

    if user:
        await message.answer(
            f"С возвращением, {user.first_name}! 👋\n",
            reply_markup=get_user_start_keyboard()
        )
        return

    await state.set_state(UserRegistration.waiting_for_contact)
    await message.answer(
        "👋 Привет! Я бот для проведения онлайн опросов.\n\n"
        "Для регистрации, пожалуйста, поделитесь своим контактом, "
        "нажав на кнопку ниже.",
        reply_markup=get_contact_keyboard()
    )

@common_router.callback_query(lambda c: c.data == "join_poll")
async def process_join_poll(callback: CallbackQuery, state: FSMContext, db: Session):
    await state.set_state(UserRegistration.waiting_for_access_code)
    await callback.message.edit_text("Пожалуйста, введите код доступа к опросу:")

@common_router.message(UserRegistration.waiting_for_access_code)
async def process_access_code(message: Message, state: FSMContext, db: Session):
    access_code = message.text.strip()
    poll = get_poll_by_access_code(db, access_code)

    if poll:
        create_poll_response(db, poll.id, message.from_user.id)
        await message.answer(f"✅ Вы успешно присоединились к опросу '{poll.title}'!")
        # TODO: Add user to the poll participants list, start the poll, etc.
        await state.clear()
    else:
        await message.answer("❌ Опрос с таким кодом доступа не найден. Пожалуйста, проверьте код и попробуйте снова.")

@common_router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🤖 Я бот для проведения онлайн опросов.\n\n"
        "Основные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/register - Зарегистрироваться\n\n"
        "Если вы администратор, используйте:\n"
        "/admin - Панель администратора"
    )

@common_router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    await state.set_state(UserRegistration.waiting_for_contact)
    await message.answer(
        "Для регистрации, пожалуйста, поделитесь своим контактом, "
        "нажав на кнопку ниже.",
        reply_markup=get_contact_keyboard()
    )

@common_router.message(F.contact, UserRegistration.waiting_for_contact)
async def handle_contact(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    contact = message.contact

    logging.info(
        f"Получен контакт от пользователя {username} (ID: {user_id}). "
        f"Телефон: {contact.phone_number}"
    )

    if contact.user_id == user_id:
        user_info = {
            'user_id': user_id,
            'username': username,
            'phone': contact.phone_number,
            'first_name': contact.first_name,
            'last_name': contact.last_name if contact.last_name else None
        }
        
        await state.update_data(user_info=user_info)
        await state.set_state(UserRegistration.waiting_for_email)
        
        logging.info(f"Успешная регистрация контакта: {user_info}")
        
        await message.answer(
            f"✅ Спасибо, {contact.first_name}!\n\n"
            f"Ваш номер {contact.phone_number} успешно сохранен.\n"
            "Теперь, пожалуйста, введите ваш email:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        logging.warning(
            f"Пользователь {username} (ID: {user_id}) попытался отправить "
            f"чужой контакт (ID: {contact.user_id})"
        )
        
        await message.answer(
            "❌ Пожалуйста, отправьте свой собственный контакт, используя кнопку ниже.",
            reply_markup=get_contact_keyboard()
        )

@common_router.message(UserRegistration.waiting_for_email)
async def handle_email(message: Message, state: FSMContext):
    email = message.text.strip()
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await message.answer(
            "❌ Неверный формат email. Пожалуйста, введите корректный email:"
        )
        return
    
    data = await state.get_data()
    user_info = data['user_info']
    user_info['email'] = email
    
    db = next(get_db())
    try:
        db_user = create_user(
            db=db,
            telegram_id=user_info['user_id'],
            username=user_info['username'],
            first_name=user_info['first_name'],
            last_name=user_info['last_name'],
            phone=user_info['phone'],
            email=email
        )
        logging.info(f"Пользователь успешно создан в базе данных: {db_user.id}")
    except Exception as e:
        logging.error(f"Ошибка при создании пользователя: {e}")
        await message.answer(
            "❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
        )
        return
    
    await state.set_state(UserRegistration.registration_complete)

    await message.answer(
        f"✅ Отлично! Регистрация завершена.\n\n"
        f"Ваши данные:\n"
        f"Имя: {user_info['first_name']}\n"
        f"Телефон: {user_info['phone']}\n"
        f"Email: {email}\n\n"
        "Теперь вы можете участвовать в опросах!"
    )
