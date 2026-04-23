from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    goal = State()
    level = State()
    frequency = State()
    preferred_time = State()
    location = State()
