import openpyxl
from openpyxl.styles import Font
from database.database import get_users_by_poll_id
from database.models import Question, QuestionResponse, PollResponse, User, Poll
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from io import BytesIO


def generate_excel_report(db: Session, poll_id: int) -> BytesIO:
    """
    Generates an Excel report for a given poll.

    Args:
        db: SQLAlchemy Session.
        poll_id: The ID of the poll.

    Returns:
        BytesIO: In-memory Excel file.
    """
    # Create a new workbook
    workbook = openpyxl.Workbook()

    # Remove default sheet
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    # Create a new sheet for poll description
    description_sheet = workbook.create_sheet("Poll Description", 0)

    # Get poll data
    poll: Optional[Poll] = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        logging.warning(f"Poll with id {poll_id} not found")
        return BytesIO()

    # Write poll data to the sheet
    description_sheet["A1"] = "Название опроса"
    description_sheet["B1"] = poll.title
    description_sheet["A2"] = "Описание"
    description_sheet["B2"] = poll.description
    description_sheet["A3"] = "Количество вопросов"
    questions = db.query(Question).filter(Question.poll_id == poll_id).order_by(Question.order).all()
    description_sheet["B3"] = len(questions)

    row_num = 4
    for question in questions:
        description_sheet[f"A{row_num}"] = f"Вопрос {question.order}"
        description_sheet[f"B{row_num}"] = question.text
        row_num += 1
        description_sheet[f"A{row_num}"] = "Варианты ответов"
        description_sheet[f"B{row_num}"] = ", ".join(question.options)
        row_num += 1
        description_sheet[f"A{row_num}"] = "Правильные ответы"
        description_sheet[f"B{row_num}"] = ", ".join(question.correct_answers)
        row_num += 2

    sheet = workbook.create_sheet("Poll Results")

    # Define headers
    headers = ["Имя и Фамилия", "Username", "Итоговый балл"]
    for question in questions:
        headers.append(f"Ответ {question.order}")
        headers.append(f"Правильный ответ {question.order}")

    # Write headers to the sheet
    for col_num, column_title in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num)
        cell.font = Font(bold=True)
        cell.value = column_title

    # Get users who participated in the poll
    user_ids = get_users_by_poll_id(db, poll_id)

    # Write data for each user
    row_num = 2
    for user_id in user_ids:
        user: Optional[User] = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logging.warning(f"User with telegram_id {user_id} not found")
            continue

        # Get user's poll response
        poll_response: Optional[PollResponse] = db.query(PollResponse).filter(PollResponse.poll_id == poll_id,
                                                                               PollResponse.user_id == user_id).first()
        if not poll_response:
            logging.warning(f"PollResponse not found for user {user_id} and poll {poll_id}")
            continue

        # Calculate total score
        total_correct_answers = db.query(QuestionResponse).filter(
            QuestionResponse.poll_response_id == poll_response.id, QuestionResponse.is_correct == True).count()
        total_questions = len(questions)

        user_data = [f"{user.first_name} {user.last_name if user.last_name else ''}", user.username, total_correct_answers]

        # Get user's question responses
        for question in questions:
            question_response: Optional[QuestionResponse] = db.query(QuestionResponse).filter(
                QuestionResponse.poll_response_id == poll_response.id,
                QuestionResponse.question_id == question.id).first()
            if question_response:
                user_data.append(", ".join(question_response.selected_answers))
                user_data.append(", ".join(question.correct_answers))
            else:
                user_data.append("N/A")
                user_data.append(", ".join(question.correct_answers))

        # Write user data to the sheet
        for col_num, cell_value in enumerate(user_data, 1):
            sheet.cell(row=row_num, column=col_num).value = cell_value

        row_num += 1

    # Create an in-memory file
    excel_file = BytesIO()
    workbook.save(excel_file)
    excel_file.seek(0)

    return excel_file
