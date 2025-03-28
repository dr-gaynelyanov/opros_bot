import re

import re

import re

import re

def parse_poll_from_file(file_content):
    questions = []
    current_question = None
    question_order = 0  # Счетчик порядковых номеров

    for line_number, line in enumerate(file_content.strip().splitlines(), start=1):
        line = line.strip()
        if not line:
            if current_question:
                questions.append(current_question)
                current_question = None
            continue

        if re.match(r"^\d+[.:)]\s", line):
            if current_question:
                questions.append(current_question)
            question_order += 1  # Увеличиваем порядковый номер
            current_question = {
                "text": line.split(" ", 1)[1],
                "options": [],
                "correct_answers": [],
                "order": question_order  # Добавляем поле order
            }
        elif current_question:
            if line.startswith("+ "):
                current_question["options"].append(line[2:])
                current_question["correct_answers"].append(line[2:])
            elif line.startswith("- "):
                current_question["options"].append(line[2:])
            else:
                raise ValueError(
                    f"Incorrect format on line {line_number}: "
                    "expected '+', '-', or a numbered question."
                )
        else:
            raise ValueError(
                f"Incorrect format on line {line_number}: "
                "expected a numbered question."
            )

    if current_question:
        questions.append(current_question)

    return questions