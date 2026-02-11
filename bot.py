import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8162365118:AAHdvqm3ewNTee8Q5izkS4s1XBh8vTO7oRk"

logging.basicConfig(level=logging.INFO)

# =========================
# ТАБЛИЦА ЦЕН
# =========================

BIKES = {
    "pcx2": {
        "name": "Honda PCX2",
        "prices": {
            "2": 340,
            "6": 320,
            "13": 300,
            "14": 280,
        }
    },
    "lead": {
        "name": "Honda Lead 125",
        "prices": {
            "2": 280,
            "6": 260,
            "13": 240,
            "14": 220,
        }
    }
}

# =========================
# ВОПРОСЫ
# =========================

QUESTIONS = [
    "Вам больше 18 лет?",
    "Есть ли у вас опыт вождения?",
    "Есть ли у вас водительское удостоверение?",
    "Понимаете ли вы ПДД?",
    "Будете ли вы ездить аккуратно?",
    "Не будете передавать байк третьим лицам?",
    "Согласны внести депозит?",
    "Есть WhatsApp?",
    "Понимаете ответственность за повреждения?",
    "Подтверждаете достоверность данных?"
]

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Honda PCX2", callback_data="bike_pcx2")],
        [InlineKeyboardButton("Honda Lead 125", callback_data="bike_lead")],
    ]

    await update.message.reply_text(
        "Выберите скутер:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# CALLBACK
# =========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    bike_key = query.data.split("_")[1]
    context.user_data["bike"] = bike_key
    context.user_data["await_days"] = True

    await query.edit_message_text(
        "Введите количество дней аренды (максимум 20):"
    )

# =========================
# ОБРАБОТКА ДНЕЙ
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("await_days"):

        try:
            days = int(update.message.text)
        except:
            await update.message.reply_text("Введите число.")
            return

        if days > 20:
            await update.message.reply_text(
                "❌ Аренда более 20 дней недоступна."
            )
            return

        bike_key = context.user_data["bike"]
        bike = BIKES[bike_key]

        # Определяем тариф автоматически
        if days <= 2:
            price_per_day = bike["prices"]["2"]
        elif days <= 6:
            price_per_day = bike["prices"]["6"]
        elif days <= 13:
            price_per_day = bike["prices"]["13"]
        else:
            price_per_day = bike["prices"]["14"]

        total = price_per_day * days

        context.user_data["await_days"] = False
        context.user_data["score"] = 0
        context.user_data["q_index"] = 0

        await update.message.reply_text(
            f"Вы выбрали:\n"
            f"{bike['name']}\n"
            f"Дней: {days}\n"
            f"Цена за день: {price_per_day}k\n"
            f"Итого: {total}k\n\n"
            f"Начинаем тестирование..."
        )

        await ask_question(update.message, context)

# =========================
# ВОПРОСЫ
# =========================

async def ask_question(message, context):

    index = context.user_data["q_index"]

    if index >= len(QUESTIONS):

        score = context.user_data["score"]

        if score >= 8:
            result = "✅ Бронирование одобрено."
        elif score >= 5:
            result = "⚠ Вам доступно бронирование только с денежным депозитом."
        else:
            result = "❌ Бронирование недоступно."

        await message.reply_text(
            f"Тест завершен.\n"
            f"Результат: {score}/10\n\n{result}"
        )
        return

    keyboard = [[
        InlineKeyboardButton("Да", callback_data="q_yes"),
        InlineKeyboardButton("Нет", callback_data="q_no"),
    ]]

    await message.reply_text(
        QUESTIONS[index],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# ОТВЕТЫ НА ТЕСТ
# =========================

async def test_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "q_yes":
        context.user_data["score"] += 1

    context.user_data["q_index"] += 1

    await ask_question(query.message, context)

# =========================
# MAIN
# =========================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="^bike_"))
    app.add_handler(CallbackQueryHandler(test_answers, pattern="^q_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()