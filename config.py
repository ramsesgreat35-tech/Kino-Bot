import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
INSTRUCTION_CHANNEL_ID = int(os.getenv("INSTRUCTION_CHANNEL_ID"))
CINEMA_CATEGORY_ID = int(os.getenv("CINEMA_CATEGORY_ID"))

_ping = os.getenv("PING_ROLE_ID", "").strip()
PING_ROLE_ID = int(_ping) if _ping.isdigit() else None

CINEMA_DATA_FILE = os.getenv("CINEMA_DATA_FILE", "cinemas.json")

# Простая валидация при старте
assert TOKEN, "❌ TOKEN не задан в .env"
assert GUILD_ID, "❌ GUILD_ID не задан"