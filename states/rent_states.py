from aiogram.fsm.state import StatesGroup, State

class RentWizard(StatesGroup):
    operation = State()
    model = State()
    package = State()
    days = State()
    time = State()
    tank = State()
    clean = State()
    equipment = State()
    payment_amount = State()
    payment_method = State()
    deposit_type = State()
    deposit_currency = State()
    deposit_method = State()