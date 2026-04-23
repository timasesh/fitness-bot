from aiogram.fsm.state import State, StatesGroup


class Water(StatesGroup):
    manual_amount = State()

