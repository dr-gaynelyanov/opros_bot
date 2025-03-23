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
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Создать опрос", callback_data="create_poll"),
            ],
            [
                InlineKeyboardButton(text="🚀 Запустить опрос", callback_data="start_poll"),
            ]
        ]
    )
    return keyboard

def get_polls_keyboard(polls: list) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру со списком опросов
    """
    keyboard = []
    for poll in polls:
        keyboard.append([InlineKeyboardButton(text=poll.title, callback_data=f"select_poll_{poll.id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_add_questions_keyboard(poll_id: int) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с кнопкой "Добавить вопросы"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="➕ Добавить вопросы", callback_data=f"add_questions_{poll_id}")
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
