from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.database import get_db, get_answer_options, create_question_response
from database.models import Poll
from sqlalchemy.orm import Session
import logging
from states.poll_states import PollPassing

poll_router = Router()

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

def create_answer_keyboard(answer_options: list, poll_id: int, question_id: int, selected_options: list = []) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с вариантами ответов.
    """
    keyboard = []
    for option in answer_options:
        if option in selected_options:
            text = f"✅ {option}"
        else:
            text = option
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"answer:{poll_id}:{question_id}:{option.replace(':', '__COLON__')}")])
    keyboard.append([InlineKeyboardButton(text="💾 Сохранить ответ", callback_data=f"save_answer:{poll_id}:{question_id}")])
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

    # Get selected options from state
    state_data = await state.get_data()
    selected_options = state_data.get(f"selected_options:{poll_id}:{question_id}", []) or []

    # Toggle selected option
    if selected_option in selected_options:
        selected_options.remove(selected_option)
    else:
        selected_options.append(selected_option)

    # Update state
    await state.update_data({f"selected_options:{poll_id}:{question_id}": selected_options})

    # Get answer options from database
    answer_options = get_answer_options(db, question_id)

    # Create new keyboard
    keyboard = create_answer_keyboard(answer_options=answer_options, poll_id=poll_id, question_id=question_id, selected_options=selected_options)

    # Edit message
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Не удалось отредактировать сообщение: {e}")

    await callback.answer()

@poll_router.callback_query(F.data.startswith("save_answer:"))
async def process_save_answer(callback: types.CallbackQuery, state: FSMContext, db: Session):
    """
    Обрабатывает сохранение ответа пользователя.
    """
    data = callback.data.split(":")
    poll_id = int(data[1])
    question_id = int(data[2])
    user_id = callback.from_user.id

    # Get selected options from state
    state_data = await state.get_data()
    selected_options = state_data.get(f"selected_options:{poll_id}:{question_id}", []) or []

    create_question_response(db, poll_id, user_id, question_id, selected_options)

    # Remove keyboard
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logging.error(f"Не удалось удалить клавиатуру: {e}")

    # Send confirmation message
    await callback.message.edit_text("✅ Ответ сохранен, ожидайте следующего вопроса.")
    await state.clear()
