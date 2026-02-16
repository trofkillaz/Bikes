from aiogram.fsm.state import StatesGroup, State

class RentStates(StatesGroup):
    choosing_bike = State()
    choosing_package = State()
    choosing_days = State()
    choosing_payment_type = State()
    choosing_currency = State()
    choosing_deposit_type = State()
    choosing_deposit_currency = State()
    choosing_deposit_payment_type = State()
    confirmation = State()