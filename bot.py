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
# БАЙКИ
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
    "Понимаете ли вы правила дорожного движения?",
    "Будете ли вы ездить аккуратно?",
    "Не планируете ли вы передавать байк третьим лицам?",
    "Согласны ли вы внести депозит?",
    "Есть ли у вас WhatsApp?",
    "Понимаете ли вы ответственность за повреждения?",
    "Подтверждаете ли вы достоверность данных?"
]

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Honda PCX2 > 340k", callback_data="bike_pcx2")],
        [InlineKeyboardButton("Honda Lead 125 > 280k", callback_data="bike_lead")],
    ]

    await update.message.reply_text(
        "Пожалуйста, выберите ваш скутер:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# ВЫБОР СРОКА
# =========================

async def choose_duration(query):
    keyboard = [
        [InlineKeyboardButton("2 < первая цена", callback_data="cat_2")],
        [InlineKeyboardButton("6 < вторая цена", callback_data="cat_6")],
        [InlineKeyboardButton("13 < третья цена", callback_data="cat_13")],
        [InlineKeyboardButton("14 + четвертая цена", callback_data="cat_14")],
    ]

    await query.edit_message_text(
        "Выберите срок аренды:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# CALLBACK
# =========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # выбор байка
    if data.startswith("bike_"):
        bike_key = data.split("_")[1]
        context.user_data["bike"] = bike_key
        await choose_duration(query)

    # выбор категории
    elif data.startswith("cat_"):
        category = data.split("_")[1]
        context.user_data["category"] = category
        context.user_data["await_days"] = True

        await query.edit_message_text(
            "Введите точное количество дней аренды:"
        )

    # ответы теста
    elif data.startswith("q_"):
        answer = data.split("_")[1]

        if answer == "yes":
            context.user_data["score"] += 1

        context.user_data["q_index"] += 1
        await ask_question(query, context)

# =========================
# ВВОД ДНЕЙ
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("await_days"):
        try:
            days = int(update.message.text)
        except:
            await update.message.reply_text("Введите число.")
            return

        bike_key = context.user_data["bike"]
        category = context.user_data["category"]
        price_per_day = BIKES[bike_key]["prices"][category]
        total = price_per_day * days

        context.user_data["await_days"] = False
        context.user_data["score"] = 0
        context.user_data["q_index"] = 0

        await update.message.reply_text(
            f"Вы выбрали:\n"
            f"{BIKES[bike_key]['name']}\n"
            f"Дней: {days}\n"
            f"Цена за день: {price_per_day}k\n"
            f"Итого: {total}k\n\n"
            f"Начинаем тестирование..."
        )

        await ask_question(update.message, context)

# =========================
# ВОПРОСЫ + СКОРИНГ
# =========================

async def ask_question(message_or_query, context):
    index = context.user_data["q_index"]

    if index >= len(QUESTIONS):
        score = context.user_data["score"]

        if score >= 8:
            result = "✅ Бронирование одобрено."
        elif score >= 5:
            result = "⚠ Вам доступно бронирование только с денежным депозитом."
        else:
            result = "❌ Бронирование недоступно."

        await message_or_query.reply_text(
            f"Тест завершен.\n"
            f"Ваш результат: {score}/10\n\n"
            f"{result}"
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data="q_yes"),
            InlineKeyboardButton("Нет", callback_data="q_no"),
        ]
    ]

    if hasattr(message_or_query, "edit_message_text"):
        await message_or_query.edit_message_text(
            QUESTIONS[index],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await message_or_query.reply_text(
            QUESTIONS[index],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# =========================
# MAIN
# =========================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()