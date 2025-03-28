from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.database import get_db, get_answer_options, create_question_response, get_users_by_poll_id
from database.models import Poll, Question, QuestionResponse, PollResponse
from sqlalchemy.orm import Session
import logging
from states.poll_states import PollPassing
from typing import Dict, List, Tuple

poll_router = Router()

TEMP_ANSWERS: Dict[Tuple[int, int, int], List[str]] = {}

async def send_question(student_id: int, question_text: str, answer_options: list, poll_id: int, question_id: int, bot):
    """
    Отправляет вопрос и варианты ответа студенту.
    """
    keyboard = create_answer_keyboard(answer_options, poll_id, question_id)
    try:
        await bot.send_message(
            student_id,
            question_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение пользователю {student_id}: {e}")


def create_answer_keyboard(answer_options: list, poll_id: int, question_id: int,
                           selected_options: list = []) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с вариантами ответов.
    """
    keyboard = []
    for option in answer_options:
        if option in selected_options:
            text = f"✅ {option}"
        else:
            text = option
        keyboard.append([InlineKeyboardButton(text=text,
                                              callback_data=f"answer:{poll_id}:{question_id}:{option.replace(':', '__COLON__')}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@poll_router.callback_query(F.data.startswith("answer:"))
async def process_answer(callback: types.CallbackQuery, state: FSMContext, db: Session):
    """
    Обрабатывает выбор варианта ответа.
    """
    data = callback.data.split(":")
    poll_id = int(data[1])
    question_id = int(data[2])
    selected_option = data[3].replace('__COLON__', ':')
    user_id = callback.from_user.id

    key = (user_id, poll_id, question_id)

    # Получаем текущие выбранные опции
    current_options = TEMP_ANSWERS.get(key, [])
    print(f"current_options: {current_options}")

    # Get selected options from state
    state_data = await state.get_data()
    selected_options = state_data.get(f"selected_options:{poll_id}:{question_id}", []) or []

    # Toggle selected option
    if selected_option in selected_options:
        selected_options.remove(selected_option)
    else:
        selected_options.append(selected_option)

    # Обновляем словарь
    TEMP_ANSWERS[key] = selected_options

    # Update state
    await state.update_data({f"selected_options:{poll_id}:{question_id}": selected_options})

    # Get answer options from database
    answer_options = get_answer_options(db, question_id)

    # Create new keyboard
    keyboard = create_answer_keyboard(answer_options=answer_options, poll_id=poll_id, question_id=question_id,
                                      selected_options=selected_options)

    # Edit message
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Не удалось отредактировать сообщение: {e}")

    await callback.answer()


async def send_results_for_question(question: Question, db: Session, bot: Bot):
    poll = question.poll
    user_ids = get_users_by_poll_id(db, poll.id)
    correct_answers = ", ".join(question.correct_answers)

    for user_id in user_ids:
        # Получаем ответ пользователя
        response = (db.query(QuestionResponse)
                    .join(PollResponse)
                    .filter(
            PollResponse.poll_id == poll.id,
                        PollResponse.user_id == user_id,
                        QuestionResponse.question_id == question.id
                    )
                    .order_by(QuestionResponse.id.desc())  # Сортировка по убыванию ID
                    .first())  # Получение первой записи после сортировки

        if not response:
            await bot.send_message(user_id, text=f"Вы не ответили на вопрос {question.order}")
            return

        user_answers = ", ".join(response.selected_answers)
        correct_answers_list = question.correct_answers
        selected_answers_list = response.selected_answers
        
        correct_count = len(set(selected_answers_list) & set(correct_answers_list))
        incorrect_count = len(selected_answers_list) - correct_count
        
        weight = 1 / len(correct_answers_list) if correct_answers_list else 0
        score = (correct_count * weight) - (incorrect_count * weight)
        score = max(0, score)
        
        result = f"Ваш балл: {score:.2f}"

        message = f"📊 Результат по вопросу:\n**Вопрос:** {question.text}\n**Ваш ответ:** {user_answers}\n**Правильный ответ:** {correct_answers}\n**Итог:** {result}"

        try:
            await bot.send_message(user_id, message, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Ошибка при отправке результатов {user_id}: {e}")
