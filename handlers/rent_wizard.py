from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.rent_states import RentWizard
from services.calc_service import calculate_total
from services.sheet_service import sheets_service

router = Router()


# ========= СТАРТ =========

@router.message(F.text == "+ Приход")
async def start_rent(message, state: FSMContext):
    await state.set_state(RentWizard.operation)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Приход", callback_data="rent|operation|income"),
            InlineKeyboardButton(text="Расход", callback_data="rent|operation|expense"),
        ]
    ])

    await message.answer("Выберите операцию:", reply_markup=kb)


# ========= ОБРАБОТКА CALLBACK =========

@router.callback_query(F.data.startswith("rent|"))
async def rent_steps(callback: CallbackQuery, state: FSMContext):
    _, step, value = callback.data.split("|")

    # ---------- Операция ----------
    if step == "operation":
        await state.update_data(operation=value)
        await state.set_state(RentWizard.model)

        models = [
            "Honda Lead",
            "Honda PCX",
            "Yamaha NVX",
            "Honda Vision",
            "Honda Airblade"
        ]

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=m, callback_data=f"rent|model|{m}")]
                for m in models
            ]
        )

        await callback.message.edit_text("Выберите модель:", reply_markup=kb)


    # ---------- Модель ----------
    elif step == "model":
        await state.update_data(model=value)
        await state.set_state(RentWizard.package)

        packages = [1, 3, 7, 14]

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{p} дней",
                        callback_data=f"rent|package|{p}"
                    )
                ] for p in packages
            ]
        )

        await callback.message.edit_text("Выберите пакет:", reply_markup=kb)


    # ---------- Пакет ----------
    elif step == "package":
        await state.update_data(package=value)
        await state.set_state(RentWizard.days)

        days_buttons = []
        for i in range(1, 21):
            days_buttons.append(
                InlineKeyboardButton(
                    text=str(i),
                    callback_data=f"rent|days|{i}"
                )
            )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[days_buttons[i:i+5] for i in range(0, 20, 5)]
        )

        await callback.message.edit_text("Выберите количество дней:", reply_markup=kb)


    # ---------- Дни ----------
    elif step == "days":
        data = await state.get_data()

        package = int(data["package"])
        selected_days = int(value)

        total = calculate_total(package, selected_days)

        await state.update_data(days=selected_days, total_amount=total)
        await state.set_state(RentWizard.time)

        times = [f"{h}:00" for h in range(9, 21)]

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t,
                        callback_data=f"rent|time|{t}"
                    )
                ] for t in times
            ]
        )

        await callback.message.edit_text(
            f"💰 Сумма к оплате: {total:,} VND\n\nВыберите время:",
            reply_markup=kb
        )


    # ---------- Время ----------
    elif step == "time":
        await state.update_data(time=value)
        await state.set_state(RentWizard.tank)

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=str(i), callback_data=f"rent|tank|{i}")
                ] for i in range(1, 7)
            ] + [[
                InlineKeyboardButton(text="Полный", callback_data="rent|tank|full")
            ]]
        )

        await callback.message.edit_text("Уровень бака:", reply_markup=kb)


    # ---------- Бак ----------
    elif step == "tank":
        await state.update_data(tank=value)
        await state.set_state(RentWizard.clean)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="+", callback_data="rent|clean|clean"),
                InlineKeyboardButton(text="-", callback_data="rent|clean|dirty")
            ]
        ])

        await callback.message.edit_text("Чистота:", reply_markup=kb)


    # ---------- Чистота ----------
    elif step == "clean":
        await state.update_data(clean=value)
        await state.set_state(RentWizard.payment_method)

        data = await state.get_data()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Нал", callback_data="rent|paymethod|cash"),
                InlineKeyboardButton(text="Безнал", callback_data="rent|paymethod|card"),
            ]
        ])

        await callback.message.edit_text(
            f"💰 Примите оплату: {data['total_amount']:,} VND",
            reply_markup=kb
        )


    # ---------- Оплата ----------
    elif step == "paymethod":
        await state.update_data(payment_method=value)

        data = await state.get_data()

        # Сохраняем в таблицу
        await sheets_service.create_rent(data)

        await callback.message.edit_text("✅ Аренда успешно создана.")
        await state.clear()

    await callback.answer()