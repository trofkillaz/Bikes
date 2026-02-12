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


# ---------- СКУТЕРЫ ----------

SCOOTERS = {
    "pcx2": {"name": "Honda PCX2", "price": 300000},
    "lead": {"name": "Honda Lead", "price": 200000},
}


# ---------- РИСК ВОПРОСЫ ----------

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


# ================= ПРОВЕРКА CONFIRMED =================

async def check_confirmed_bookings(context: ContextTypes.DEFAULT_TYPE):
    keys = await redis_client.keys("booking:*")

    for key in keys:
        raw = await redis_client.get(key)
        if not raw:
            continue

        data = json.loads(raw)

        if data.get("status") == "confirmed":

            final_text = data.get("final_text")

            if not final_text:
                continue

            try:
                await context.bot.send_message(
                    chat_id=int(data["client_id"]),
                    text=final_text
                )

                data["status"] = "closed"
                await redis_client.set(key, json.dumps(data))

            except Exception as e:
                logging.error(f"Ошибка отправки клиенту: {e}")


# ---------- START ----------

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
    await update.message.reply_text("Введите контакт (WhatsApp / Telegram):")
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

    await redis_client.set(f"booking:{booking_id}", json.dumps(booking_data))

    await query.edit_message_text(