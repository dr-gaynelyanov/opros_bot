def translate_exception(exception_message):
    """
    Переводит текст исключения на русский язык.

    :param exception_message: Текст исключения (строка).
    :return: Переведенное сообщение на русском языке.
    """
    # Словарь с переводами
    translations = {
        "Incorrect format on line {line_number}: expected a numbered question.":
            "Неверный формат в строке {line_number}: ожидался пронумерованный вопрос.",
        "Incorrect format on line {line_number}: expected '+', '-', or a numbered question.":
            "Неверный формат в строке {line_number}: ожидался ответ ('+' или '-') или пронумерованный вопрос.",
        "Incorrect format: no correct answer for question '{question_text}'.":
            "Неверный формат: отсутствует правильный ответ для вопроса '{question_text}'.",
        "Unknown error":
            "Неизвестная ошибка"
    }

    # Извлечение параметров из текста исключения
    def extract_params(message):
        params = {}
        if "on line" in message:
            line_number = int(message.split("on line")[1].split(":")[0].strip())
            params["line_number"] = line_number
        if "for question" in message:
            question_text = message.split("for question")[1].split(".")[0].strip().strip("'")
            params["question_text"] = question_text
        return params

    # Проверяем все шаблоны переводов
    for template, translation in translations.items():
        try:
            # Подставляем параметры из исходного сообщения в шаблон
            if exception_message == template.format(**extract_params(exception_message)):
                return translation.format(**extract_params(exception_message))
        except KeyError:
            continue

    # Если перевод не найден, возвращаем оригинальное сообщение или "Неизвестная ошибка"
    return translations.get("Unknown error", exception_message)