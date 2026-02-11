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
    ContextTypes,
)

TOKEN = "8162365118:AAHdvqm3ewNTee8Q5izkS4s1XBh8vTO7oRk"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ========================
# СТАРТ
# ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Начать бронирование", callback_data="start_booking")]
    ]
    await update.message.reply_text(
        "Добро пожаловать 🛵\nНажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================
# ВЫБОР БАЙКА
# ========================

async def choose_bike(query):
    keyboard = [
        [InlineKeyboardButton("Honda PCX2 > 340k", callback_data="bike_pcx2")],
        [InlineKeyboardButton("Honda Lead 125 > 280k", callback_data="bike_lead")],
        [InlineKeyboardButton("Honda AirBlade > 300k", callback_data="bike_air")],
    ]

    await query.edit_message_text(
        "Пожалуйста, выберите ваш скутер:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================
# ВЫБОР СРОКА
# ========================

async def choose_duration(query):
    keyboard = [
        [InlineKeyboardButton("1 день", callback_data="dur_1")],
        [InlineKeyboardButton("3 дня", callback_data="dur_3")],
        [InlineKeyboardButton("7 дней", callback_data="dur_7")],
        [InlineKeyboardButton("30 дней", callback_data="dur_30")],
    ]

    await query.edit_message_text(
        "Выберите срок аренды:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================
# РИСК ТЕСТ (пример)
# ========================

async def risk_test(query):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="risk_yes")],
        [InlineKeyboardButton("Нет", callback_data="risk_no")],
    ]

    await query.edit_message_text(
        "Были ли у вас аварии за последний год?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================
# CALLBACK HANDLER
# ========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "start_booking":
        await choose_bike(query)

    elif data.startswith("bike_"):
        context.user_data["bike"] = data
        await choose_duration(query)

    elif data.startswith("dur_"):
        context.user_data["duration"] = data
        await risk_test(query)

    elif data == "risk_yes":
        await query.edit_message_text(
            "❌ К сожалению, бронирование недоступно."
        )

    elif data == "risk_no":
        await query.edit_message_text(
            "✅ Риск менеджмент пройден.\n\n"
            "Пожалуйста, напишите одним сообщением:\n"
            "WhatsApp + Название отеля + Номер комнаты"
        )

# ========================
# MAIN
# ========================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()