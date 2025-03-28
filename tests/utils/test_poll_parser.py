import pytest

from utils.poll_parser import parse_poll_from_file


def test_parse_poll_from_file_valid_input():
    file_content = """
    1. Что делает оператор `break` в цикле?
    + Прерывает цикл
    - Пропускает текущую итерацию
    - Возвращает значение из цикла
    - Запускает цикл заново
    """
    expected_questions = [
        {
            'text': 'Что делает оператор `break` в цикле?',
            'options': ['Прерывает цикл', 'Пропускает текущую итерацию', 'Возвращает значение из цикла',
                        'Запускает цикл заново'],
            'correct_answers': ['Прерывает цикл'],
            'order': 1
        }
    ]
    actual_questions = parse_poll_from_file(file_content)
    assert actual_questions == expected_questions


def test_parse_poll_from_file_multiple_questions():
    file_content = """
1. Question 1
+ Correct answer 1
- Incorrect answer 1

2. Question 2
- Incorrect answer 2
+ Correct answer 2
"""
    expected_questions = [
        {
            'text': 'Question 1',
            'options': ['Correct answer 1', 'Incorrect answer 1'],
            'correct_answers': ['Correct answer 1'],
            'order': 1
        },
        {
            'text': 'Question 2',
            'options': ['Incorrect answer 2', 'Correct answer 2'],
            'correct_answers': ['Correct answer 2'],
            'order': 2
        }
    ]
    actual_questions = parse_poll_from_file(file_content)
    assert actual_questions == expected_questions


def test_parse_poll_from_file_empty_file():
    file_content = ""
    expected_questions = []
    actual_questions = parse_poll_from_file(file_content)
    assert actual_questions == expected_questions


def test_parse_poll_from_file_no_questions():
    file_content = """
This is just some text
without any questions.
"""
    with pytest.raises(ValueError) as exc_info:
        parse_poll_from_file(file_content)
    assert str(exc_info.value) == "Incorrect format on line 1: expected a numbered question."


def test_parse_poll_from_file_incorrect_question_format():
    file_content = """
        1. Question 1
        + Correct answer 1
        - Incorrect answer 1

        Question 2 without number
        - Incorrect answer 2
        + Correct answer 2
        """
    with pytest.raises(ValueError) as exc_info:
        question_list = parse_poll_from_file(file_content)
        print(question_list)

    # Проверяем сообщение исключения
    assert str(exc_info.value) == "Incorrect format on line 5: expected a numbered question."


def test_parse_poll_invalid_answer_format():
    file_content = """
        1. Question 1
        + Correct answer 1
        - Incorrect answer 1

        2. Question 2
        Invalid answer format
        + Correct answer 2
        - Incorrect answer 2
    """
    with pytest.raises(ValueError) as exc_info:
        parse_poll_from_file(file_content)

    # Проверяем сообщение исключения
    assert str(exc_info.value) == "Incorrect format on line 6: expected '+', '-', or a numbered question."


def test_parse_poll_empty_question_text():
    file_content = """
        1. Question 1
        + Correct answer 1
        - Incorrect answer 1

        2.
        + Correct answer 2
        - Incorrect answer 2
    """
    with pytest.raises(ValueError) as exc_info:
        parse_poll_from_file(file_content)

    # Проверяем сообщение исключения
    assert str(exc_info.value) == "Incorrect format on line 5: expected a numbered question."


def test_parse_poll_invalid_question_number():
    file_content = """
        1. Question 1
        + Correct answer 1
        - Incorrect answer 1

        A. Invalid question number
        + Correct answer 2
        - Incorrect answer 2
    """
    with pytest.raises(ValueError) as exc_info:
        parse_poll_from_file(file_content)

    # Проверяем сообщение исключения
    assert str(exc_info.value) == "Incorrect format on line 5: expected a numbered question."


def test_parse_poll_answers_without_question():
    file_content = """
        + Correct answer 1
        - Incorrect answer 1

        1. Question 1
        + Correct answer 2
        - Incorrect answer 2
        """
    with pytest.raises(ValueError) as exc_info:
        parse_poll_from_file(file_content)
    assert str(exc_info.value) == "Incorrect format on line 1: expected a numbered question."


def test_parse_poll_multiple_empty_lines():
    file_content = """
        1. Question 1
        + Correct answer 1
        - Incorrect answer 1



        Invalid line between questions

        2. Question 2
        + Correct answer 2
        - Incorrect answer 2
    """
    with pytest.raises(ValueError) as exc_info:
        parse_poll_from_file(file_content)

    # Проверяем сообщение исключения
    assert str(exc_info.value) == "Incorrect format on line 7: expected a numbered question."
