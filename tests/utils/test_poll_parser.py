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
    expected_questions = []
    actual_questions = parse_poll_from_file(file_content)
    assert actual_questions == expected_questions


def test_parse_poll_from_file_incorrect_question_format():
    file_content = """
1. Question 1
+ Correct answer 1
- Incorrect answer 1

Question 2 without number
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
        # Question 2 should be ignored as it has incorrect format
    ]
    actual_questions = parse_poll_from_file(file_content)
    assert actual_questions == expected_questions
