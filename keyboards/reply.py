from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_contact_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой для отправки контакта
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="📱 Поделиться контактом", request_contact=True)
        ]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard 