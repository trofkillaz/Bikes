from aiogram import Router
from aiogram.types import Message
from keyboards.menu import main_menu

router = Router()

@router.message()
async def show_menu(message: Message):
    await message.answer(
        "Главное меню",
        reply_markup=main_menu()
    )