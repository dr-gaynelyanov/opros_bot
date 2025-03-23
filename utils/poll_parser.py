import re

def parse_poll_from_file(file_content):
    """
    Parses poll questions and answers from a text file content.

    Returns:
        list: A list of dictionaries, each representing a question with text, options, and correct_answers.
    """
    questions = []
    current_question = None
    question_order = 0

    for line in file_content.strip().splitlines():
        line = line.strip()
        if not line:
            if current_question:
                questions.append(current_question)
                current_question = None
            continue

        if re.match(r"^\d+\.\s", line):
            if current_question:
                questions.append(current_question)
            current_question = {
                "text": line.split(". ", 1)[1],
                "options": [],
                "correct_answers": [],
                "order": question_order + 1
            }
            question_order += 1
        elif current_question:
            if line.startswith("+ "):
                current_question["options"].append(line[2:])
                current_question["correct_answers"].append(line[2:])
            elif line.startswith("- "):
                current_question["options"].append(line[2:])

    if current_question:
        questions.append(current_question)

    return questions
