import os
import json
import uuid
import logging
import asyncio
import redis.asyncio as redis

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
REDIS_1 = os.getenv("REDIS_1")
REDIS_2 = os.getenv("REDIS_2")

redis_booking = redis.from_url(REDIS_1, decode_responses=True)
redis_event = redis.from_url(REDIS_2, decode_responses=True)

(
    RISK,
    SCOOTER,
    DAYS,
    NAME,
    HOTEL,
    ROOM,
    CONTACT,
    CONFIRM
) = range(8)

# ---------------- СКУТЕРЫ ----------------

SCOOTERS = {
    "pcx2": {"name": "Honda PCX2", "price": 300000},
    "lead": {"name": "Honda Lead", "price": 200000},
}

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🛵 Добро пожаловать! Выберите скутер:")

    keyboard = [
        [InlineKeyboardButton("Honda PCX2", callback_data="pcx2")],
        [InlineKeyboardButton("Honda Lead", callback_data="lead")],
    ]

    await update.message.reply_text(
        "Выберите модель:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return SCOOTER

# ---------------- SCOOTER ----------------

async def scooter_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["scooter"] = query.data
    await query.edit_message_text("Введите количество дней аренды:")
    return DAYS

async def days_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["days"] = int(update.message.text)
    except:
        await update.message.reply_text("Введите число.")
        return DAYS

    await update.message.reply_text("Введите ваше имя:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Введите название отеля:")
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

    booking_data = {
        "booking_id": booking_id,
        "client_id": update.effective_user.id,
        "username": update.effective_user.username,
        "scooter": scooter["name"],
        "days": context.user_data["days"],
        "total": total,
        "deposit": "—",
        "equipment": [],
        "name": context.user_data["name"],
        "hotel": context.user_data["hotel"],
        "room": context.user_data["room"],
        "contact": context.user_data["contact"],
        "status": "new"
    }

    await redis_booking.set(
        f"booking:{booking_id}",
        json.dumps(booking_data),
        ex=600
    )

    await redis_event.set(
        f"event:{uuid.uuid4()}",
        json.dumps({
            "type": "new_booking",
            "booking_id": booking_id
        }),
        ex=600
    )

    await update.message.reply_text(
        "⏳ Заявка отправлена менеджеру. Ожидайте подтверждения."
    )

    return ConversationHandler.END

# ==============================
# LISTENER (полностью исправлен)
# ==============================

async def listen_events(app):
    print("Client listener started")

    while True:
        try:
            keys = []
            async for key in redis_event.scan_iter("event:update:*"):
                keys.append(key)

            for key in keys:
                raw = await redis_event.get(key)
                if not raw:
                    continue

                event = json.loads(raw)

                if event.get("type") != "booking_update":
                    continue

                booking_id = event["booking_id"]

                raw_booking = await redis_booking.get(f"booking:{booking_id}")
                if not raw_booking:
                    await redis_event.delete(key)
                    continue

                booking = json.loads(raw_booking)

                equipment_text = "\n".join(booking.get("equipment", []))
                if not equipment_text:
                    equipment_text = "Без доп. комплектации"

                text = (
                    f"✅ Заявка завершена\n\n"
                    f"🛵 {booking['scooter']}\n"
                    f"📆 {booking['days']} дней\n"
                    f"💵 {booking['total']}\n"
                    f"💰 Депозит: {booking.get('deposit','—')}\n\n"
                    f"📦 Комплектация:\n{equipment_text}\n\n"
                    f"👤 {booking['name']}\n"
                    f"🏨 {booking['hotel']} | {booking['room']}\n"
                    f"📞 {booking['contact']}"
                )

                await app.bot.send_message(
                    chat_id=booking["client_id"],
                    text=text
                )

                await redis_event.delete(key)

        except Exception as e:
            logging.error(f"Client listener error: {e}")

        await asyncio.sleep(2)

# ==============================
# MAIN
# ==============================

async def post_init(app):
    asyncio.create_task(listen_events(app))

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
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.post_init = post_init

    print("Client bot started")
    app.run_polling()

if __name__ == "__main__":
    main()