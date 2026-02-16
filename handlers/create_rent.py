from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from states.rent_states import RentStates
from data.bikes import BIKES
from services.timer_service import start_rent_timer

router = Router()

@router.message(F.text == "➕ Приход")
async def start_rent(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=number, callback_data=f"bike_{number}")]
            for number in BIKES.keys()
        ]
    )
    await message.answer("Выберите номер", reply_markup=keyboard)
    await state.set_state(RentStates.choosing_bike)

@router.callback_query(RentStates.choosing_bike, F.data.startswith("bike_"))
async def choose_bike(callback: CallbackQuery, state: FSMContext):
    bike_number = callback.data.split("_")[1]

    await state.update_data(bike=bike_number)
    await callback.answer()

    await callback.message.answer("Выберите пакет: 1 / 3 / 7 / 14")

    await state.set_state(RentStates.choosing_package)

    await start_rent_timer(state)