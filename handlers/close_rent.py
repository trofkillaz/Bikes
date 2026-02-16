from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.sheet_service import close_rent_by_number

router = Router()


@router.callback_query(F.data.startswith("open_"))
async def open_rent_card(callback: CallbackQuery):
    request_number = callback.data.split("_")[1]

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Закрыть аренду",
        callback_data=f"close_{request_number}"
    )
    builder.adjust(1)

    await callback.message.answer(
        f"Заявка №{request_number}\n\nНажмите кнопку ниже для закрытия.",
        reply_markup=builder.as_markup()
    )

    await callback.answer()


@router.callback_query(F.data.startswith("close_"))
async def close_rent(callback: CallbackQuery):
    request_number = callback.data.split("_")[1]

    await close_rent_by_number(request_number)

    await callback.message.answer(f"✅ Заявка №{request_number} закрыта и перенесена в архив.")
    await callback.answer()