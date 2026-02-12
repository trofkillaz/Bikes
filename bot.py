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
    ContextTypes,
    filters,
    ConversationHandler,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

(SCOOTER, DAYS, NAME, HOTEL, ROOM, CONTACT, CONFIRM) = range(7)

SCOOTERS = {
    "pcx2": {"name": "Honda PCX2", "price": 300000},
    "lead": {"name": "Honda Lead", "price": 200000},
}


# ---------- START ----------

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


# ---------- SCOOTER ----------

async def scooter_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["scooter"] = query.data
    await query.edit_message_text("Введите количество дней аренды:")
    return DAYS


# ---------- DAYS ----------

async def days_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["days"] = int(update.message.text)
    except:
        await update.message.reply_text("Введите число.")
        return DAYS

    await update.message.reply_text("Введите ваше имя:")
    return NAME


# ---------- NAME ----------

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Введите название отеля:")
    return HOTEL


# ---------- HOTEL ----------

async def get_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hotel"] = update.message.text
    await update.message.reply_text("Введите номер комнаты:")
    return ROOM


# ---------- ROOM ----------

async def get_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["room"] = update.message.text
    await update.message.reply_text("Введите контакт (WhatsApp / Telegram):")
    return CONTACT


# ---------- CONTACT ----------

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text

    scooter = SCOOTERS[context.user_data["scooter"]]
    total = scooter["price"] * context.user_data["days"]
    context.user_data["total"] = total

    text = (
        f"📄 Проверьте данные:\n\n"
        f"🛵 {scooter['name']}\n"
        f"📆 {context.user_data['days']} дней\n"
        f"💰 {total} VND\n\n"
        f"👤 {context.user_data['name']}\n"
        f"🏨 {context.user_data['hotel']}\n"
        f"🚪 {context.user_data['room']}\n"
        f"📞 {context.user_data['contact']}"
    )

    keyboard = [[InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")]]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CONFIRM


# ---------- CONFIRM ----------

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    booking_id = str(uuid.uuid4())
    scooter = SCOOTERS[context.user_data["scooter"]]

    booking_data = {
        "booking_id": booking_id,
        "client_id": update.effective_user.id,
        "username": update.effective_user.username,
        "scooter": scooter["name"],
        "days": context.user_data["days"],
        "total": context.user_data["total"],
        "name": context.user_data["name"],
        "hotel": context.user_data["hotel"],
        "room": context.user_data["room"],
        "contact": context.user_data["contact"],
        "status": "new"
    }

    await redis_client.set(f"booking:{booking_id}", json.dumps(booking_data))

    await query.edit_message_text(
        "⏳ Заявка отправлена. Ожидайте подтверждения."
    )

    return ConversationHandler.END


# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SCOOTER: [CallbackQueryHandler(scooter_selected)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, days_input)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hotel)],
            ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_room)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            CONFIRM: [CallbackQueryHandler(confirm, pattern="^confirm$")],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()