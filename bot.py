import os
import json
import uuid
import logging
import redis.asyncio as redis

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
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

r = redis.from_url(REDIS_URL, decode_responses=True)

# ================== СОСТОЯНИЯ ==================

(
    RISK,
    SCOOTER,
    DAYS,
    NAME,
    HOTEL,
    ROOM,
    CONTACT,
    DEPOSIT_INPUT,
) = range(8)

# ================== СКУТЕРЫ ==================

SCOOTERS = {
    "pcx2": {"name": "Honda PCX2", "price": 300000},
    "lead": {"name": "Honda Lead", "price": 200000},
}

# ================== РИСК ==================

RISK_QUESTIONS = [
    ("Права категории A?", 2, -1),
    ("Международные права?", 1, 0),
    ("Стаж более 2 лет?", 2, 0),
    ("Были ДТП за последние 2 года?", -2, 2),
    ("Возраст старше 23 лет?", 1, 0),
]

# =========================================================
#                      КЛИЕНТ
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["risk_score"] = 0
    context.user_data["risk_step"] = 0
    return await ask_risk(update, context)

async def ask_risk(update, context):
    step = context.user_data["risk_step"]
    q = RISK_QUESTIONS[step][0]

    kb = [[
        InlineKeyboardButton("✅ Да", callback_data="risk_yes"),
        InlineKeyboardButton("❌ Нет", callback_data="risk_no"),
    ]]

    await update.message.reply_text(
        f"📊 Оценка риска\n\n{q}",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return RISK

async def handle_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    step = context.user_data["risk_step"]
    yes_score = RISK_QUESTIONS[step][1]
    no_score = RISK_QUESTIONS[step][2]

    if query.data == "risk_yes":
        context.user_data["risk_score"] += yes_score
    else:
        context.user_data["risk_score"] += no_score

    context.user_data["risk_step"] += 1

    if context.user_data["risk_step"] >= len(RISK_QUESTIONS):

        if context.user_data["risk_score"] <= 1:
            await query.edit_message_text("❌ Высокий риск. Аренда невозможна.")
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton("Honda PCX2", callback_data="pcx2")],
            [InlineKeyboardButton("Honda Lead", callback_data="lead")],
        ]

        await query.edit_message_text("🛵 Выберите скутер:")
        await query.message.reply_text(
            "Выберите модель:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SCOOTER

    return await ask_risk(query, context)

async def scooter_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["scooter"] = query.data
    await query.edit_message_text("Введите количество дней:")
    return DAYS

async def days_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["days"] = int(update.message.text)
    except:
        await update.message.reply_text("Введите число.")
        return DAYS

    await update.message.reply_text("Введите имя:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Введите отель:")
    return HOTEL

async def get_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hotel"] = update.message.text
    await update.message.reply_text("Введите номер комнаты:")
    return ROOM

async def get_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["room"] = update.message.text
    await update.message.reply_text("Введите контакт:")
    return CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text

    scooter = SCOOTERS[context.user_data["scooter"]]
    total = scooter["price"] * context.user_data["days"]

    booking_id = str(uuid.uuid4())

    booking = {
        "booking_id": booking_id,
        "client_id": update.effective_user.id,
        "username": update.effective_user.username,
        "scooter": scooter["name"],
        "days": context.user_data["days"],
        "total": total,
        "deposit": "",
        "equipment": [],
        "name": context.user_data["name"],
        "hotel": context.user_data["hotel"],
        "room": context.user_data["room"],
        "contact": context.user_data["contact"],
        "status": "new",
    }

    await r.set(f"booking:{booking_id}", json.dumps(booking))

    text = (
        f"🆕 Новая заявка\n\n"
        f"🛵 {booking['scooter']}\n"
        f"📆 {booking['days']} дней\n"
        f"💵 {booking['total']} VND\n\n"
        f"👤 {booking['name']}\n"
        f"🏨 {booking['hotel']} | {booking['room']}\n"
        f"📞 {booking['contact']}"
    )

    kb = [[
        InlineKeyboardButton("✅ Принять", callback_data=f"accept:{booking_id}")
    ]]

    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=text,
        reply_markup=InlineKeyboardMarkup(kb)
    )

    await update.message.reply_text("⏳ Заявка отправлена менеджеру.")
    return ConversationHandler.END

# =========================================================
#                    МЕНЕДЖЕР
# =========================================================

async def manager_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, booking_id = query.data.split(":")
    raw = await r.get(f"booking:{booking_id}")
    if not raw:
        return

    booking = json.loads(raw)

    # --- Принятие ---
    if action == "accept":
        booking["status"] = "in_progress"
        booking["manager"] = update.effective_user.username

        kb = [[
            InlineKeyboardButton("2 шлема", callback_data=f"helmets:{booking_id}"),
            InlineKeyboardButton("2 дождевика", callback_data=f"rain:{booking_id}")
        ]]

        await query.edit_message_reply_markup(InlineKeyboardMarkup(kb))
        await r.set(f"booking:{booking_id}", json.dumps(booking))
        return

    # --- Комплектация ---
    if action == "helmets":
        booking["equipment"].append("2 шлема")

    if action == "rain":
        booking["equipment"].append("2 дождевика")

    if action == "deposit":
        context.user_data["deposit_booking"] = booking_id
        await query.message.reply_text("Введите депозит:")
        return DEPOSIT_INPUT

    if action == "finish":
        equipment = "\n".join(booking["equipment"]) or "Без доп. комплектации"

        text = (
            f"✅ Заявка завершена\n\n"
            f"🛵 {booking['scooter']}\n"
            f"📆 {booking['days']} дней\n"
            f"💵 {booking['total']} VND\n"
            f"💰 Депозит: {booking['deposit']}\n\n"
            f"📦 Комплектация:\n{equipment}\n\n"
            f"👤 {booking['name']}\n"
            f"🏨 {booking['hotel']} | {booking['room']}\n"
            f"📞 {booking['contact']}\n\n"
            f"👨‍💼 @{booking['manager']}"
        )

        booking["status"] = "completed"
        await r.set(f"booking:{booking_id}", json.dumps(booking))

        await query.edit_message_text(text)

        await context.bot.send_message(
            chat_id=booking["client_id"],
            text=text
        )
        return ConversationHandler.END

    kb = [[
        InlineKeyboardButton("Ввести депозит", callback_data=f"deposit:{booking_id}"),
        InlineKeyboardButton("Завершить", callback_data=f"finish:{booking_id}")
    ]]

    await query.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    await r.set(f"booking:{booking_id}", json.dumps(booking))

async def deposit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_id = context.user_data.get("deposit_booking")
    raw = await r.get(f"booking:{booking_id}")
    if not raw:
        return ConversationHandler.END

    booking = json.loads(raw)
    booking["deposit"] = update.message.text  # любой текст разрешён

    await r.set(f"booking:{booking_id}", json.dumps(booking))
    await update.message.reply_text("Депозит сохранён. Нажмите Завершить в группе.")
    return ConversationHandler.END

# =========================================================
#                        MAIN
# =========================================================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            RISK: [CallbackQueryHandler(handle_risk, pattern="^risk_")],
            SCOOTER: [CallbackQueryHandler(scooter_selected)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, days_input)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hotel)],
            ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_room)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(manager_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_input))

    app.run_polling()

if __name__ == "__main__":
    main()