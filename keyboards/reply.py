from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

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

def get_admin_start_inline_keyboard() -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру для админов при команде /start
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="📝 Создать опрос", callback_data="create_poll")
        ]]
    )
    return keyboard

def get_admin_start_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру для админов при команде /start (устаревшая)
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="📝 Создать опрос")
        ]],
        resize_keyboard=True
    )
    return keyboard
