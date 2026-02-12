iimport os
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
REDIS_1 = os.getenv("REDIS_1")  # booking
REDIS_2 = os.getenv("REDIS_2")  # events

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

# ---------------- РИСК ----------------

RISK_QUESTIONS = [
    ("Права категории A?", 2, -1),
    ("Международные права?", 1, 0),
    ("Стаж более 2 лет?", 2, 0),
    ("Были ДТП за последние 2 года?", -2, 2),
    ("Срок аренды более 15 дней?", -1, 1),
    ("Совместное пользование?", 0, 1),
    ("Выезд за пределы провинции?", 0, 1),
    ("В стране более 7 дней?", 1, 0),
    ("Возраст старше 23 лет?", 1, 0),
    ("Ранее арендовал во Вьетнаме?", 2, 1),
]

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["risk_score"] = 0
    context.user_data["risk_step"] = 0
    await ask_risk_question(update, context)
    return RISK

async def ask_risk_question(update, context):
    step = context.user_data["risk_step"]
    question = RISK_QUESTIONS[step][0]

    keyboard = [[
        InlineKeyboardButton("✅ Да", callback_data="risk_yes"),
        InlineKeyboardButton("❌ Нет", callback_data="risk_no"),
    ]]

    if update.message:
        await update.message.reply_text(
            f"📊 Оценка риска\n\n{question}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.callback_query.edit_message_text(
            f"📊 Оценка риска\n\n{question}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
        score = context.user_data["risk_score"]

        if score >= 8:
            risk_level = "🟢 Низкий риск"
        elif score >= 3:
            risk_level = "🟡 Средний риск"
        else:
            risk_level = "🔴 Высокий риск"

        context.user_data["risk_level"] = risk_level

        if score <= 2:
            await query.edit_message_text(
                f"{risk_level}\n\n❌ К сожалению, мы не можем подтвердить аренду."
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"{risk_level}\n\nПереходим к выбору скутера."
        )

        keyboard = [
            [InlineKeyboardButton("Honda PCX2", callback_data="pcx2")],
            [InlineKeyboardButton("Honda Lead", callback_data="lead")],
        ]

        await query.message.reply_text(
            "🛵 Выберите скутер:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return SCOOTER

    await ask_risk_question(update, context)
    return RISK

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
    context.user_data["total"] = total

    text = (
        f"📄 Проверьте данные:\n\n"
        f"🛵 {scooter['name']}\n"
        f"📆 {context.user_data['days']} дней\n"
        f"💰 {total} VND\n\n"
        f"👤 {context.user_data['name']}\n"
        f"🏨 {context.user_data['hotel']}\n"
        f"🚪 {context.user_data['room']}\n"
        f"📞 {context.user_data['contact']}\n\n"
        f"📊 {context.user_data['risk_level']}"
    )

    keyboard = [[InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")]]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CONFIRM

# ---------------- CONFIRM ----------------

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
        "risk_score": context.user_data["risk_score"],
        "risk_level": context.user_data["risk_level"],
        "status": "new"
    }

    await redis_booking.set(
        f"booking:{booking_id}",
        json.dumps(booking_data)
    )

    await query.edit_message_text(
        "⏳ Заявка отправлена менеджеру. Ожидайте подтверждения."
    )

    return ConversationHandler.END

# ---------------- LISTENER ----------------

async def listen_events(app):
    while True:
        try:
            keys = await redis_event.keys("event:*")

            for key in keys:
                raw = await redis_event.get(key)
                if not raw:
                    continue

                try:
                    event = json.loads(raw)
                except:
                    continue

                if event.get("type") != "booking_update":
                    continue

                booking_id = event.get("booking_id")
                if not booking_id:
                    continue

                booking_raw = await redis_booking.get(f"booking:{booking_id}")
                if not booking_raw:
                    continue

                booking = json.loads(booking_raw)

                await process_update(app, booking, event)

                await redis_event.delete(key)

        except Exception as e:
            logging.error(f"Listener error: {e}")

        await asyncio.sleep(3)

async def process_update(app, booking, event):
    client_id = booking["client_id"]

    if event["status"] == "approved":
        text = (
            f"✅ Заявка завершена\n\n"
            f"🛵 {booking['scooter']}\n"
            f"📆 {booking['days']} дней\n"
            f"💵 {event.get('final_total', booking['total'])}\n"
            f"💰 Депозит: {event.get('deposit', '-')}\n\n"
            f"🎁 Комплектация:\n"
            f"• 2 шлема\n"
            f"• 2 дождевика\n\n"
            f"👤 {booking['name']}\n"
            f"🏨 {booking['hotel']} | {booking['room']}\n"
            f"📞 {booking['contact']}\n"
            f"📊 {booking['risk_level']}\n\n"
            f"👨‍💼 {event.get('manager','')}"
        )
    else:
        text = "❌ К сожалению, заявка не подтверждена."

    await app.bot.send_message(chat_id=client_id, text=text)

# ---------------- MAIN ----------------

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
            CONFIRM: [CallbackQueryHandler(confirm, pattern="^confirm$")],
        },
        fallbacks=[],
    )

    app.add_handler(conv)

    asyncio.get_event_loop().create_task(listen_events(app))

    app.run_polling()

if __name__ == "__main__":
    main()