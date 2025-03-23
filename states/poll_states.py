from aiogram.fsm.state import State, StatesGroup

class CreatePollStates(StatesGroup):
    waiting_for_poll_title = State()
    waiting_for_poll_description = State()
    poll_created = State()
