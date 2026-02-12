import os
import json
import uuid
import logging
import redis.asyncio as redis

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")

logging.basicConfig(level=logging.INFO)

# Redis (без падения если ошибка)
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        logging.info("Redis connected")
    except Exception as e:
        logging.error(f"Redis connection failed: {e}")
else:
    logging.warning("REDIS_URL not set")

# =========================
# СОСТОЯНИЯ
# =========================

(
    SCOOTER,
    DAYS,
    NAME,
    HOTEL,
    ROOM,
    CONTACT,
    CONFIRM
) = range(7)

# =========================
# ДАННЫЕ
# =========================

SCOOTERS = {
    "pcx": {"name": "🛵 Honda PCX", "price": 300000},
    "airblade": {"name": "🛵 Honda AirBlade", "price": 250000},
}

# =========================
# СТАРТ
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Honda PCX", callback_data="pcx"),
            InlineKeyboardButton("Honda AirBlade", callback_data="airblade"),
        ]
    ]

    await update.message.reply_text(
        "Выберите байк:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SCOOTER

# =========================
# ВЫБОР БАЙКА
# =========================

async def choose_scooter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    scooter_key = query.data
    context.user_data["scooter"] = scooter_key

    await query.edit_message_text("На сколько дней аренда?")
    return DAYS

# =========================
# ДНИ
# =========================

async def get_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = int(update.message.text)
    context.user_data["days"] = days

    scooter = SCOOTERS[context.user_data["scooter"]]
    total = scooter["price"] * days
    context.user_data["total"] = total

    await update.message.reply_text("Ваше имя?")
    return NAME

# =========================
# ИМЯ
# =========================

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Отель?")
    return HOTEL

# =========================
# ОТЕЛЬ
# =========================

async def get_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hotel"] = update.message.text
    await update.message.reply_text("Номер комнаты?")
    return ROOM

# =========================
# КОМНАТА
# =========================

async def get_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["room"] = update.message.text
    await update.message.reply_text("Контакт (телефон / Telegram)?")
    return CONTACT

# =========================
# КОНТАКТ
# =========================

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text

    scooter = SCOOTERS[context.user_data["scooter"]]

    summary = (
        f"🛵 {scooter['name']}\n"
        f"📆 {context.user_data['days']} дней\n"
        f"💵 {context.user_data['total']} VND\n\n"
        f"🎁 Комплектация:\n"
        f"• 2 шлема\n"
        f"• 2 дождевика\n\n"
        f"👤 {context.user_data['name']}\n"
        f"🏨 {context.user_data['hotel']} | {context.user_data['room']}\n"
        f"📞 {context.user_data['contact']}\n\n"
        f"Подтвердить?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
        ]
    ]

    await update.message.reply_text(
        summary,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CONFIRM

# =========================
# ПОДТВЕРЖДЕНИЕ
# =========================

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

    if redis_client:
        try:
            await redis_client.set(
                f"booking:{booking_id}",
                json.dumps(booking_data)
            )
        except Exception as e:
            logging.error(f"Redis save error: {e}")

    await query.edit_message_text(
        "⏳ Заявка отправлена менеджеру.\nОжидайте подтверждения."
    )

    return ConversationHandler.END

# =========================
# ОТМЕНА
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Заявка отменена.")
    return ConversationHandler.END

# =========================
# MAIN
# =========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SCOOTER: [CallbackQueryHandler(choose_scooter)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_days)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hotel)],
            ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_room)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            CONFIRM: [
                CallbackQueryHandler(confirm, pattern="confirm"),
                CallbackQueryHandler(cancel, pattern="cancel"),
            ],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()