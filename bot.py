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
    ConversationHandler,
)

TOKEN = "8162365118:AAHdvqm3ewNTee8Q5izkS4s1XBh8vTO7oRk"

# 🔥 ВСТАВЬ ID ГРУППЫ
GROUP_ID = -1003726782924

logging.basicConfig(level=logging.INFO)

(
    SCOOTER,
    TARIFF,
    DAYS,
    TEST,
    NAME,
    CONTACT,
    CONFIRM,
) = range(7)

SCOOTERS = {
    "pcx2": {
        "name": "Honda PCX2",
        "prices": {"2": 340000, "6": 300000, "13": 260000, "14+": 230000},
    },
    "lead": {
        "name": "Honda Lead",
        "prices": {"2": 240000, "6": 210000, "13": 190000, "14+": 170000},
    },
}

SCORING = [
    ("Права категории A?", 2, -1),
    ("Международные права?", 1, 0),
    ("Стаж более 2 лет?", 2, 0),
    ("ДТП за последние 2 года?", -2, 2),
    ("Срок аренды более 15 дней?", -1, 1),
    ("Совместное пользование?", 0, 1),
    ("Выезд за пределы провинции?", 0, 1),
    ("В стране более 7 дней?", 1, 0),
    ("Возраст старше 23 лет?", 1, 0),
    ("Ранее арендовал во Вьетнаме?", 2, 1),
]


# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Honda PCX2", callback_data="pcx2")],
        [InlineKeyboardButton("Honda Lead", callback_data="lead")],
    ]
    await update.message.reply_text(
        "🛵 Выберите скутер:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SCOOTER


# ---------------- SCOOTER ----------------

async def scooter_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["scooter"] = query.data

    keyboard = [
        [InlineKeyboardButton("До 2 дней", callback_data="2")],
        [InlineKeyboardButton("До 6 дней", callback_data="6")],
        [InlineKeyboardButton("До 13 дней", callback_data="13")],
        [InlineKeyboardButton("14+ дней", callback_data="14+")],
    ]

    await query.edit_message_text(
        "📆 Выберите тариф:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return TARIFF


# ---------------- TARIFF ----------------

async def tariff_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["tariff"] = query.data
    await query.edit_message_text("Введите количество дней (максимум 20):")
    return DAYS


# ---------------- DAYS ----------------

async def days_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text)
    except:
        await update.message.reply_text("Введите число.")
        return DAYS

    if days > 20:
        await update.message.reply_text("❌ Максимальный срок аренды 20 дней.")
        return DAYS

    context.user_data["days"] = days

    scooter = SCOOTERS[context.user_data["scooter"]]
    tariff = context.user_data["tariff"]

    price_per_day = scooter["prices"][tariff]
    total = price_per_day * days

    context.user_data["price_per_day"] = price_per_day
    context.user_data["total"] = total
    context.user_data["score"] = 0
    context.user_data["question_index"] = 0

    return await ask_question(update, context)


# ---------------- TEST ----------------

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data["question_index"]

    if index >= len(SCORING):
        return await finish_test(update, context)

    question = SCORING[index][0]

    keyboard = [[
        InlineKeyboardButton("Да", callback_data="yes"),
        InlineKeyboardButton("Нет", callback_data="no"),
    ]]

    await update.message.reply_text(
        f"❓ {question}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return TEST


async def test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    index = context.user_data["question_index"]
    yes_score = SCORING[index][1]
    no_score = SCORING[index][2]

    if query.data == "yes":
        context.user_data["score"] += yes_score
    else:
        context.user_data["score"] += no_score

    context.user_data["question_index"] += 1

    if context.user_data["question_index"] >= len(SCORING):
        return await finish_test_callback(query, context)

    question = SCORING[context.user_data["question_index"]][0]

    keyboard = [[
        InlineKeyboardButton("Да", callback_data="yes"),
        InlineKeyboardButton("Нет", callback_data="no"),
    ]]

    await query.edit_message_text(
        f"❓ {question}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return TEST


async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


async def finish_test_callback(query, context):
    score = context.user_data["score"]

    if score <= 2:
        await query.edit_message_text("🔴 Высокий риск. В бронировании отказано.")
        return ConversationHandler.END

    status = "🟢 Низкий риск" if score >= 8 else "🟡 Средний риск"
    context.user_data["risk_status"] = status

    await query.edit_message_text(
        f"{status}\n\nВведите ваше имя:"
    )
    return NAME


# ---------------- NAME ----------------

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "Пожалуйста, отправьте одним сообщением:\n\nWhatsApp или Telegram\nНазвание отеля\nНомер комнаты"
    )
    return CONTACT


# ---------------- CONTACT ----------------

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text

    scooter_name = SCOOTERS[context.user_data["scooter"]]["name"]

    text = (
        f"📄 Проверьте данные:\n\n"
        f"🛵 Скутер: {scooter_name}\n"
        f"📆 Дней: {context.user_data['days']}\n"
        f"💵 Цена/день: {context.user_data['price_per_day']} VND\n"
        f"💰 Итого: {context.user_data['total']} VND\n\n"
        f"👤 Имя: {context.user_data['name']}\n"
        f"📍 Контакт:\n{context.user_data['contact']}\n\n"
        f"{context.user_data['risk_status']}"
    )

    keyboard = [[
        InlineKeyboardButton("✅ Подтвердить бронирование", callback_data="confirm")
    ]]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CONFIRM


# ---------------- CONFIRM ----------------

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    scooter_name = SCOOTERS[context.user_data["scooter"]]["name"]

    group_text = (
        "🆕 НОВАЯ БРОНЬ\n\n"
        f"🛵 Скутер: {scooter_name}\n"
        f"📆 Дней: {context.user_data['days']}\n"
        f"💰 Итого: {context.user_data['total']} VND\n\n"
        f"👤 Имя: {context.user_data['name']}\n"
        f"📍 Контакт:\n{context.user_data['contact']}\n\n"
        f"{context.user_data['risk_status']}"
    )

    # 🔥 Отправка в группу
    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=group_text,
    )

    await query.edit_message_text(
        "⏳ Заявка отправлена. Ожидайте подтверждения."
    )

    return ConversationHandler.END


# ---------------- MAIN ----------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SCOOTER: [CallbackQueryHandler(scooter_selected)],
            TARIFF: [CallbackQueryHandler(tariff_selected)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, days_input)],
            TEST: [CallbackQueryHandler(test_answer)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            CONFIRM: [CallbackQueryHandler(confirm)],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()