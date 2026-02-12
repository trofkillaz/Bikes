import logging
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# ======================
# НАСТРОЙКИ
# ======================

TOKEN = "8162365118:AAHdvqm3ewNTee8Q5izkS4s1XBh8vTO7oRk"
GROUP_ID = -1003726782924  # <-- ВСТАВЬ СВОЙ ID ГРУППЫ

# ======================
# ЛОГИ
# ======================

logging.basicConfig(level=logging.INFO)

# ======================
# СОСТОЯНИЯ
# ======================

NAME, PHONE, DATE, CONFIRM = range(4)

# ======================
# ХЕНДЛЕРЫ
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите ваше имя:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Введите номер телефона:")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Введите дату бронирования:")
    return DATE


async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text

    text = (
        "Проверьте данные:\n\n"
        f"👤 Имя: {context.user_data['name']}\n"
        f"📞 Телефон: {context.user_data['phone']}\n"
        f"📅 Дата: {context.user_data['date']}\n\n"
        "Подтвердить?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm":

        text = (
            "🆕 НОВАЯ ЗАЯВКА\n\n"
            f"👤 Имя: {context.user_data['name']}\n"
            f"📞 Телефон: {context.user_data['phone']}\n"
            f"📅 Дата: {context.user_data['date']}"
        )

        # Отправка в группу
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=text,
        )

        await query.edit_message_text("✅ Заявка отправлена!")

    else:
        await query.edit_message_text("❌ Заявка отменена.")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


# ======================
# MAIN
# ======================

def main():
    print("CLIENT BOT STARTED")

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            CONFIRM: [CallbackQueryHandler(confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    app.run_polling()


if __name__ == "__main__":
    main()