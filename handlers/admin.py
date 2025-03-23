from database.models import Poll
from keyboards.reply import get_admin_start_inline_keyboard, get_add_questions_keyboard
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from database.database import get_db, get_user_by_telegram_id, is_admin, add_admin, remove_admin, get_admin_count, \
    get_admins, create_poll_db, create_question, get_polls_by_creator, get_users_by_poll_id
from sqlalchemy.orm import Session
from states.admin_states import AdminStates
from states.poll_states import CreatePollStates
from utils.poll_parser import parse_poll_from_file
import logging
from keyboards.reply import get_polls_keyboard, get_send_first_question_keyboard
from handlers.poll import send_question
from database.models import Question

admin_router = Router()

def get_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def process_user_id_input(message: types.Message, state: FSMContext, db: Session, 
                              is_admin_action: bool, current_user_id: int) -> bool:
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный ID пользователя (только цифры).")
        return False
    
    if is_admin_action and user_id == current_user_id:
        await message.answer("❌ Вы не можете удалить самого себя из администраторов.")
        return False
    
    user = get_user_by_telegram_id(db, user_id)
    if not user:
        await message.answer("❌ Пользователь с таким ID не найден в базе данных.")
        return False
    
    if is_admin_action:
        if not is_admin(db, user_id):
            await message.answer("❌ Этот пользователь не является администратором.")
            return False
    else:
        if is_admin(db, user_id):
            await message.answer("❌ Этот пользователь уже является администратором.")
            return False
    
    await state.update_data(user_id=user_id)
    return True

@admin_router.message(Command("admin"))

async def admin_command(message: types.Message, db: Session):
    if not is_admin(db, message.from_user.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    
    await message.answer(
        "Панель управления администратора",
        reply_markup=get_admin_start_inline_keyboard()
    )

@admin_router.callback_query(lambda c: c.data == "start_poll")
async def process_start_poll(callback: types.CallbackQuery, state: FSMContext, db: Session):
    user_id = callback.from_user.id
    polls = get_polls_by_creator(db, user_id)

    if not polls:
        await callback.message.edit_text("У вас пока нет созданных опросов.")
        return

    await callback.message.edit_text(
        "Выберите опрос для запуска:",
        reply_markup=get_polls_keyboard(polls)
    )

@admin_router.callback_query(F.data.startswith("select_poll_"))
async def process_select_poll(callback: types.CallbackQuery, state: FSMContext, db: Session, bot: Bot):
    poll_id = int(callback.data.split("_")[-1])
    poll = db.query(Poll).filter(Poll.id == poll_id).first()

    if not poll:
        await callback.message.edit_text("❌ Опрос не найден.")
        return
    
    await callback.message.edit_text(
        f"Код доступа к опросу '{poll.title}':\n\n`{poll.access_code}`",
        parse_mode="Markdown",
        reply_markup=get_send_first_question_keyboard(poll.id)
    )

@admin_router.callback_query(F.data.startswith("send_first_question_"))
async def process_send_first_question(callback: types.CallbackQuery, bot: Bot, db: Session):
    poll_id = int(callback.data.split("_")[-1])

    # Get the first question for the poll
    question = db.query(Question).filter(Question.poll_id == poll_id).order_by(Question.order).first()

    if not question:
        await callback.message.answer("❌ В этом опросе пока нет вопросов.")
        return

    # Get the poll object
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        await callback.message.answer("❌ Опрос не найден.")
        return

    # Get list of users who joined the poll (PollResponse)
    user_ids = get_users_by_poll_id(db, poll_id)

    if not user_ids:
        await callback.message.answer("❌ К этому опросу еще никто не присоединился.")
        return

    answer_options = question.options
    question_text = question.text

    admin_message = f"**Вопрос:** {question_text}\n\n**Варианты ответов:**\n"
    for i, option in enumerate(answer_options):
        admin_message += f"{i+1}. {option}\n"

    admin_message += "\n**Правильные ответы:**\n"
    if question.correct_answers:
        for i, option in enumerate(question.correct_answers):
            admin_message += f"{i+1}. {option}\n"
    else:
        admin_message += "Нет правильных ответов.\n"

    await callback.message.answer(admin_message, parse_mode="Markdown")

    for user_id in user_ids:
        try:
            await send_question(user_id, question_text, answer_options, poll_id, question.id, bot)
        except Exception as e:
            logging.error(f"Не удалось отправить вопрос пользователю {user_id}: {e}")

    await callback.message.answer(f"Первый вопрос отправлен {len(user_ids)} пользователям!")


@admin_router.callback_query(lambda c: c.data == "create_poll")
async def process_create_poll(callback: types.CallbackQuery, state: FSMContext, db: Session):
    await state.set_state(CreatePollStates.waiting_for_poll_title)
    await callback.message.edit_text("Пожалуйста, введите название опроса:")

@admin_router.message(CreatePollStates.waiting_for_poll_title)
async def process_poll_title(message: types.Message, state: FSMContext):
    await state.update_data(poll_title=message.text)
    await state.set_state(CreatePollStates.waiting_for_poll_description)
    await message.answer("Теперь, пожалуйста, введите описание опроса:")

@admin_router.message(CreatePollStates.waiting_for_poll_description)
async def process_poll_description(message: types.Message, state: FSMContext, db: Session):
    data = await state.get_data()
    poll_title = data.get('poll_title')
    poll_description = message.text
    user_id = message.from_user.id

    poll = create_poll_db(db, title=poll_title, description=poll_description, created_by=user_id)
    
    await state.update_data(poll_description=poll_description, poll_id=poll.id)
    await state.set_state(CreatePollStates.poll_created)
    await message.answer(
        f"Опрос '{poll_title}' успешно создан!\n\n"
        "Теперь вы можете добавить вопросы к опросу.",
        reply_markup=get_add_questions_keyboard(poll.id)
    )

@admin_router.callback_query(F.data.startswith("add_questions_"))
async def process_add_questions(callback: types.CallbackQuery, state: FSMContext, db: Session):
    poll_id = int(callback.data.split("_")[-1])
    await state.update_data(poll_id=poll_id)
    await state.set_state(CreatePollStates.waiting_for_questions_file)
    await callback.message.edit_text(
        "Пожалуйста, отправьте текстовый файл с вопросами для опроса.\n\n"
        "**Формат файла:**\n"
        "Каждый вопрос должен начинаться с номера, за которым следует точка и пробел. "
        "Варианты ответов должны начинаться с `+ ` (для правильных ответов) или `- ` (для неправильных ответов). "
        "Вопросы должны быть разделены пустыми строками.\n\n"
        "**Пример:**\n"
        "```\n"
        "1. Столица России?\n"
        "+ Москва\n"
        "- Санкт-Петербург\n"
        "- Казань\n"
        "\n"
        "2. Какая река самая длинная в мире?\n"
        "- Нил\n"
        "+ Амазонка\n"
        "- Янцзы\n"
        "```",
        parse_mode="Markdown"
    )

@admin_router.message(CreatePollStates.waiting_for_questions_file, F.document)
async def process_questions_file(message: types.Message, state: FSMContext, db: Session):
    data = await state.get_data()
    poll_id = data.get('poll_id')

    if not poll_id:
        await message.answer("❌ Ошибка: ID опроса не найден. Пожалуйста, создайте опрос заново.")
        await state.clear()
        return

    document = message.document
    file_id = document.file_id
    file = await message.bot.get_file(file_id)
    file_path = file.file_path

    try:
        downloaded_file = await message.bot.download_file(file_path)
        file_content = downloaded_file.read().decode('utf-8')
        questions = parse_poll_from_file(file_content)

        if not questions:
            await message.answer(
                "❌ Ошибка: В файле не найдены вопросы в правильном формате. "
                "Пожалуйста, проверьте формат файла и отправьте его снова."
            )
            return

        for question_data in questions:
            create_question(db, poll_id, question_data['text'], question_data['options'], question_data['correct_answers'], question_data['order'])

        await message.answer(f"✅ Вопросы успешно добавлены к опросу!", reply_markup=ReplyKeyboardRemove())
        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка при обработке файла с вопросами: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке файла с вопросами. "
            "Пожалуйста, попробуйте снова.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()

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
    if await process_user_id_input(message, state, db, False, message.from_user.id):
        data = await state.get_data()
        user_id = data['user_id']
        user = get_user_by_telegram_id(db, user_id)
        
        await state.set_state(AdminStates.confirming_add_admin)
        await message.answer(
            f"Вы уверены, что хотите сделать администратором пользователя:\n"
            f"ID: {user_id}\n"
            f"Имя: {user.first_name} {user.last_name or ''}\n"
            f"Username: @{user.username or 'не указан'}",
            reply_markup=get_confirm_keyboard("add_admin")
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

@admin_router.callback_query(lambda c: c.data == "remove_admin")
async def process_remove_admin(callback: types.CallbackQuery, state: FSMContext, db: Session):
    if not is_admin(db, callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return
    
    admin_count = get_admin_count(db)
    if admin_count <= 1:
        await callback.answer("❌ Невозможно удалить последнего администратора!", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_admin_id)
    await callback.message.edit_text(
        "Пожалуйста, введите ID администратора, которого хотите удалить.\n"
        "ID можно получить, переслав сообщение от пользователя боту @getidsbot"
    )

@admin_router.message(AdminStates.waiting_for_admin_id)
async def process_admin_id(message: types.Message, state: FSMContext, db: Session):
    if await process_user_id_input(message, state, db, True, message.from_user.id):
        data = await state.get_data()
        user_id = data['user_id']
        user = get_user_by_telegram_id(db, user_id)
        
        await state.set_state(AdminStates.confirming_remove_admin)
        await message.answer(
            f"Вы уверены, что хотите удалить из администраторов пользователя:\n"
            f"ID: {user_id}\n"
            f"Имя: {user.first_name} {user.last_name or ''}\n"
            f"Username: @{user.username or 'не указан'}",
            reply_markup=get_confirm_keyboard("remove_admin")
        )

@admin_router.callback_query(lambda c: c.data == "confirm_remove_admin", AdminStates.confirming_remove_admin)
async def process_confirm_remove_admin(callback: types.CallbackQuery, state: FSMContext, db: Session):
    data = await state.get_data()
    user_id = data['user_id']
    
    user = remove_admin(db, user_id)
    if user:
        await callback.message.edit_text(
            f"✅ Пользователь {user.first_name} {user.last_name or ''} "
            f"(@{user.username or 'не указан'}) успешно удален из администраторов."
        )
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении администратора."
        )
    
    await state.clear()

@admin_router.callback_query(lambda c: c.data == "cancel_remove_admin", AdminStates.confirming_remove_admin)
async def process_cancel_remove_admin(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Удаление администратора отменено.")
    await state.clear()

@admin_router.callback_query(lambda c: c.data == "list_admins")
async def process_list_admins(callback: types.CallbackQuery, db: Session):
    if not is_admin(db, callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return
    
    admins = get_admins(db)
    if not admins:
        await callback.message.edit_text("В системе пока нет администраторов.")
        return
    
    admin_list_str = "📋 Список администраторов:\n\n"
    for admin in admins:
        admin_list_str += (
            f"ID: {admin.telegram_id}\n"
            f"Имя: {admin.first_name} {admin.last_name or ''}\n"
            f"Username: @{admin.username or 'не указан'}\n"
            f"Email: {admin.email}\n"
            f"Телефон: {admin.phone}\n"
            f"Дата регистрации: {admin.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"-------------------\n"
        )
    
    await callback.message.edit_text(admin_list_str)
