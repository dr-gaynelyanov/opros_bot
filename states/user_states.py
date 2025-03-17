from aiogram.fsm.state import State, StatesGroup


class UserRegistration(StatesGroup):
    waiting_for_contact = State()
    waiting_for_email = State()
    registration_complete = State()
