from aiogram.fsm.state import State, StatesGroup

class CreatePollStates(StatesGroup):
    waiting_for_poll_title = State()
    waiting_for_poll_description = State()
    poll_created = State()
    waiting_for_questions_file = State()
    waiting_for_questions_text = State()
    waiting_for_custom_access_code = State()

class PollPassing(StatesGroup):
    current_question_index = State()
    questions_list = State()
    poll_id = State()
