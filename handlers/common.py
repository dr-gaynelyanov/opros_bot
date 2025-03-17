from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards.reply import get_contact_keyboard
from states.user_states import UserRegistration
import logging
import re

common_router = Router()

@common_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(UserRegistration.waiting_for_contact)
    await message.answer(
        "👋 Привет! Я бот для проведения онлайн опросов.\n\n"
        "Для регистрации, пожалуйста, поделитесь своим контактом, "
        "нажав на кнопку ниже.",
        reply_markup=get_contact_keyboard()
    )

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
    
    await state.set_state(UserRegistration.registration_complete)

    logging.info(f"Успешная регистрация email для пользователя {user_info['username']}: {email}")
    
    await message.answer(
        f"✅ Отлично! Регистрация завершена.\n\n"
        f"Ваши данные:\n"
        f"Имя: {user_info['first_name']}\n"
        f"Телефон: {user_info['phone']}\n"
        f"Email: {email}\n\n"
        "Теперь вы можете участвовать в опросах!"
    )