from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.sheet_service import get_active_rents

router = Router()


@router.message(F.text == "📂 Байки в работе")
async def show_active_rents(message: Message):
    rents = await get_active_rents()

    if not rents:
        await message.answer("Нет активных заявок.")
        return

    builder = InlineKeyboardBuilder()

    for rent in rents:
        builder.button(
            text=f"{rent['request_number']} | {rent['plate']}",
            callback_data=f"open_{rent['request_number']}"
        )

    builder.button(text="🔄 Обновить список", callback_data="refresh_active")
    builder.adjust(1)

    await message.answer("📂 Активные заявки:", reply_markup=builder.as_markup())


@router.callback_query(F.data == "refresh_active")
async def refresh_active(callback: CallbackQuery):
    await show_active_rents(callback.message)
    await callback.answer()