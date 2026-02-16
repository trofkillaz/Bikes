import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

RENT_TIMEOUT_MINUTES = 10
FUEL_PRICE = 20000
WASH_PRICE = 40000