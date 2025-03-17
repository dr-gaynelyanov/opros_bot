from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_user_id = State()  
    confirming_add_admin = State() 