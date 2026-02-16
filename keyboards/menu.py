from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📂 Открытые заявки")],
            [KeyboardButton(text="➕ Приход")],
            [KeyboardButton(text="➖ Расход")]
        ],
        resize_keyboard=True
    )