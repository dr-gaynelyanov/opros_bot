from datetime import datetime

from sqlalchemy import func

from database.models import Poll, PollResponse, QuestionResponse
from keyboards.reply import get_admin_start_inline_keyboard, get_add_questions_keyboard, \
    get_admin_question_control_keyboard, get_admin_control_keyboard
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from database.database import get_db, get_user_by_telegram_id, is_admin, add_admin, remove_admin, get_admin_count, \
    get_admins, create_poll_db, create_question, get_polls_by_creator, get_users_by_poll_id, create_question_response
from sqlalchemy.orm import Session
from states.admin_states import AdminStates
from states.poll_states import CreatePollStates
from utils.message_exception_translator import translate_exception
from utils.poll_parser import parse_poll_from_file
import logging
from keyboards.reply import get_polls_keyboard, get_send_first_question_keyboard
from handlers.poll import send_question, send_results_for_question, TEMP_ANSWERS
from database.models import Question
from utils.report_generator import generate_excel_report
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramForbiddenError

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
        reply_markup=get_admin_control_keyboard()
        )


@admin_router.message(CreatePollStates.waiting_for_questions_text, F.text)
async def process_questions_text(message: types.Message, state: FSMContext, db: Session):
    data = await state.get_data()
    poll_id = data.get('poll_id')
    if not poll_id:
        await message.answer("❌ Ошибка: ID опроса не найден. Пожалуйста, создайте опрос заново.")
        await state.clear()
        return

    file_content = message.text
    try:
        questions = parse_poll_from_file(file_content)
    except ValueError as e:
        translated_error_message = translate_exception(str(e))
        logging.error(f"Ошибка при обработке текста с вопросами: {e}")
        await message.answer(
            f"❌ Произошла ошибка: {translated_error_message}. "
            "Пожалуйста, исправьте текст и отправьте его снова.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    for question_data in questions:
        create_question(db, poll_id, question_data['text'], question_data['options'],
                        question_data['correct_answers'], question_data['order'])

    await message.answer(f"✅ Вопросы успешно добавлены к опросу!", reply_markup=ReplyKeyboardRemove())
    await state.clear()


@admin_router.message(Command("initialize_admin"))
async def initialize_admin_command(message: types.Message, db: Session):
    """
    Назначает текущего пользователя администратором, если нет других админов в базе данных.
    """
    admin_count = get_admin_count(db)
    if admin_count == 0:
        user = add_admin(db, message.from_user.id)
        if user:
            await message.answer(
                f"✅ Вы успешно инициализированы как администратор.\n"
                f"ID: {user.telegram_id}\n"
                f"Имя: {user.first_name} {user.last_name or ''}\n"
                f"Username: @{user.username or 'не указан'}"
            )
        else:
            await message.answer("❌ Произошла ошибка при инициализации администратора. Возможно, вам следует сначала зарегистрироваться через /start")
    else:
        await message.answer("❌ Инициализация администратора не требуется. Администраторы уже существуют.")


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
    poll.is_active = True
    db.commit()
    print(poll.access_code)
    await callback.message.edit_text(
        f"Код доступа к опросу {poll.title}:\n\n{poll.access_code}",
        reply_markup=get_send_first_question_keyboard(poll.id)
    )


@admin_router.callback_query(F.data.startswith("send_first_question_"))
async def process_send_first_question(callback: types.CallbackQuery, bot: Bot, db: Session, state: FSMContext):
    poll_id = int(callback.data.split("_")[-1])

    # Получаем все вопросы опроса
    questions = db.query(Question).filter(Question.poll_id == poll_id).order_by(Question.order).all()
    if not questions:
        await callback.message.answer("❌ В этом опросе пока нет вопросов.")
        return

    # Сохраняем данные в FSM
    await state.update_data(
        questions_list=[q.id for q in questions],
        current_question_index=0,
        poll_id=poll_id
    )

    # Отправляем первый вопрос
    await send_next_question(callback, bot, db, state)


async def send_next_question(callback: types.CallbackQuery, bot: Bot, db: Session, state: FSMContext):
    data = await state.get_data()
    questions_list = data.get('questions_list', [])
    current_index = data.get('current_question_index', 0)
    poll_id = data.get('poll_id')

    if current_index >= len(questions_list):
        await callback.message.answer("Все вопросы уже отправлены")
        return

    question_id = questions_list[current_index]
    question = db.query(Question).filter(Question.id == question_id).first()

    question.is_active = True
    db.commit()

    if not question:
        await callback.message.answer(f"❌ Вопрос {current_index + 1} не найден")
        return

    # Получаем пользователей опроса
    user_ids = get_users_by_poll_id(db, poll_id)
    if not user_ids:
        await callback.message.answer("❌ Нет пользователей для опроса")
        return

    # Формируем сообщение для админа
    admin_message = (
        f"**Вопрос {current_index + 1}:** {question.text}\n"
        "**Варианты ответов:**\n"
    )

    admin_keyboard = get_admin_question_control_keyboard(poll_id, question.id)

    for i, option in enumerate(question.options, 1):
        admin_message += f"{i}. {option}\n"
    admin_message += "\n**Правильные ответы:**\n"
    for i, answer in enumerate(question.correct_answers, 1):
        admin_message += f"{i}. {answer}\n"

    # Отправляем вопрос пользователям
    success_count = 0
    for user_id in user_ids:
        try:
            await send_question(
                student_id=user_id,
                question_text=question.text,
                answer_options=question.options,
                poll_id=poll_id,
                question_id=question.id,
                bot=bot
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Ошибка отправки вопроса {question.id} пользователю {user_id}: {e}")

    # Обновляем состояние
    await state.update_data(current_question_index=current_index + 1)

    # Отправляем подтверждение администратору
    await callback.message.answer(
        text=f"✅ Вопрос {current_index + 1} отправлен {success_count}/{len(user_ids)} пользователям",
    )
    question_details_message = await bot.send_message(
        chat_id=callback.from_user.id,
        text=admin_message,
        parse_mode="Markdown",
        reply_markup=admin_keyboard
    )
    await state.update_data(question_details_message=question_details_message)


@admin_router.callback_query(F.data.startswith("finish_question_"))
async def process_finish_question(callback: types.CallbackQuery, db: Session, bot: Bot, state: FSMContext):
    poll_id, question_id = map(int, callback.data.split("_")[2:])
    data = await state.get_data()

    # Получаем всех пользователей опроса
    user_ids = get_users_by_poll_id(db, poll_id)

    for user_id in user_ids:
        key = (user_id, poll_id, question_id)
        selected_answers = TEMP_ANSWERS.get(key, [])
        print(f"selected_answers: {selected_answers}")

        # Создаем запись в БД
        create_question_response(db, poll_id, user_id, question_id, selected_answers)

        # Удаляем временные данные
        if key in TEMP_ANSWERS:
            del TEMP_ANSWERS[key]

    # Получаем вопрос из БД
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        await callback.answer("Вопрос не найден", show_alert=True)
        return

    await send_results_for_question(question, db, bot)
    next_question_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Перейти к следующему вопросу", callback_data=f"next_question_{poll_id}")]
    ])

    await callback.message.answer(
        f"✅ Прием ответов на вопрос {question.order} завершен",
        reply_markup=next_question_keyboard
    )
    question_details_message: types.Message = data.get("question_details_message")
    try:
        await bot.edit_message_reply_markup(
            chat_id=callback.from_user.id,
            message_id=question_details_message.message_id,
            reply_markup=None
        )
    except Exception as e:
        logging.error(f"Ошибка при удалении клавиатуры для {callback.from_user.id}: {e}")


@admin_router.callback_query(F.data.startswith("next_question_"))
async def process_next_question(callback: types.CallbackQuery, bot: Bot, db: Session, state: FSMContext):
    data = await state.get_data()
    poll_id = int(callback.data.split("_")[2])
    questions_list = data.get('questions_list', [])
    current_index = data.get('current_question_index', 0)

    if current_index >= len(questions_list):
        # Calculate total score
        poll_id = int(callback.data.split("_")[2])
        questions = db.query(Question).filter(Question.poll_id == poll_id).order_by(Question.order).all()
        user_ids = get_users_by_poll_id(db, poll_id)

        # Set completed_at for all users
        for user_id in user_ids:
            poll_response = db.query(PollResponse).filter(
                PollResponse.poll_id == poll_id,
                PollResponse.user_id == user_id,
                PollResponse.completed_at == None  # noqa
            ).first()
            if poll_response:
                poll_response.completed_at = datetime.utcnow()
                db.commit()

        # Set poll is_active to False
        poll = db.query(Poll).filter(Poll.id == poll_id).first()
        if poll:
            poll.is_active = False
            db.commit()

        await callback.message.answer(text="Опрос завершен, можете посмотреть отчет")

        # Generate Excel report
        excel_file = generate_excel_report(db, poll_id)
        file = BufferedInputFile(excel_file.read(), filename=f"poll_{poll_id}_results.xlsx")
        await bot.send_document(callback.from_user.id, document=file)

        # Send results to each user
        for user_id in user_ids:
            poll_response = db.query(PollResponse).filter(PollResponse.poll_id == poll_id, PollResponse.user_id == user_id).first()
            if poll_response:
                total_score = db.query(func.sum(QuestionResponse.score)).filter(
                    QuestionResponse.poll_response_id == poll_response.id
                ).scalar() or 0.0

                # Округляем до двух знаков после запятой
                total_score = round(total_score, 2)

                await bot.send_message(
                    user_id,
                    f"Опрос завершен! Вы набрали {total_score} баллов"
                )

        return

    await send_next_question(callback, bot, db, state)


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
    await state.update_data(poll_description=message.text)
    await state.set_state(CreatePollStates.waiting_for_custom_access_code)
    await message.answer(
        "Теперь, пожалуйста, введите код доступа к опросу. "
        "Вы можете ввести свой код или нажать кнопку 'Сгенерировать случайный код'.",
        reply_markup=get_access_code_keyboard()
    )


def get_access_code_keyboard() -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с кнопкой для генерации случайного кода доступа.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎲 Сгенерировать случайный код", callback_data="generate_access_code")
            ]
        ]
    )
    return keyboard


@admin_router.message(CreatePollStates.waiting_for_custom_access_code, F.text)
async def process_custom_access_code(message: types.Message, state: FSMContext, db: Session):
    data = await state.get_data()
    poll_title = data.get('poll_title')
    poll_description = data.get('poll_description')
    user_id = message.from_user.id
    custom_access_code = message.text.strip()  # Получаем введенный пользователем код доступа

    poll = create_poll_db(db, title=poll_title, description=poll_description, created_by=user_id, access_code=custom_access_code)

    await state.update_data(poll_id=poll.id)
    await state.set_state(CreatePollStates.poll_created)
    await message.answer(
        f"Опрос '{poll_title}' успешно создан с кодом доступа: {custom_access_code}!\n\n"
        "Теперь вы можете добавить вопросы к опросу.",
        reply_markup=get_add_questions_keyboard(poll.id)
    )


@admin_router.callback_query(lambda c: c.data == "generate_access_code", CreatePollStates.waiting_for_custom_access_code)
async def process_generate_access_code(callback: types.CallbackQuery, state: FSMContext, db: Session):
    data = await state.get_data()
    poll_title = data.get('poll_title')
    poll_description = data.get('poll_description')
    user_id = callback.from_user.id
    import uuid
    generated_access_code = str(uuid.uuid4())[:8]  # Генерация случайного кода

    poll = create_poll_db(db, title=poll_title, description=poll_description, created_by=user_id, access_code=generated_access_code)

    await state.update_data(poll_id=poll.id)
    await state.set_state(CreatePollStates.poll_created)
    await callback.message.edit_text(
        f"Опрос '{poll_title}' успешно создан со случайным кодом доступа: {generated_access_code}!\n\n"
        "Теперь вы можете добавить вопросы к опросу.",
        reply_markup=get_add_questions_keyboard(poll.id)
    )


@admin_router.callback_query(F.data.startswith("add_questions_"))
async def process_add_questions(callback: types.CallbackQuery, state: FSMContext, db: Session):
    poll_id = int(callback.data.split("_")[-1])
    await state.update_data(poll_id=poll_id)
    if callback.data.startswith("add_questions_file_"):
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
    elif callback.data.startswith("add_questions_text_"):
        await state.set_state(CreatePollStates.waiting_for_questions_text)
        await callback.message.edit_text(
            "Пожалуйста, введите вопросы для опроса текстом, соблюдая формат:\n\n"
            "**Формат текста:**\n"
            "1. Вопрос 1\n"
            "+ Верный ответ 1\n"
            "- Неверный ответ 1\n"
            "- Неверный ответ 2\n"
            "\n"
            "2. Вопрос 2\n"
            "+ Верный ответ 1\n"
            "- Неверный ответ 1\n"
            "- Неверный ответ 2\n"
            "\n"
            "И так далее. Каждый вопрос с новой строки, варианты ответов начинаются с '+' или '-'.",
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
        try:
            questions = parse_poll_from_file(file_content)
        except ValueError as e:
            translated_error_message = translate_exception(str(e))
            logging.error(f"Ошибка при обработке файла с вопросами: {e}")
            await message.answer(
                f"❌ Произошла ошибка: {translated_error_message}. "
                "Пожалуйста, исправьте файл и отправьте его снова.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        for question_data in questions:
            create_question(db, poll_id, question_data['text'], question_data['options'],
                            question_data['correct_answers'], question_data['order'])

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
