from aiogram.fsm.state import State, StatesGroup


class UserRegistration(StatesGroup):
    choosing_registration_type = State()
    waiting_for_contact = State()
    waiting_for_email = State()
    registration_complete = State()
    waiting_for_access_code = State()
