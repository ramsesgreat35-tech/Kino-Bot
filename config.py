import os
from dotenv import load_dotenv

# Загружаем .env, если он есть (на хостинге он может игнорироваться)
load_dotenv()

TOKEN = os.getenv("TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID_STR = os.getenv("GUILD_ID")

if not GUILD_ID_STR:
    raise ValueError("❌ Переменная GUILD_ID не найдена! Добавь её в панели Bothost.")

GUILD_ID = int(GUILD_ID_STR)
INSTRUCTION_CHANNEL_ID = int(os.getenv("INSTRUCTION_CHANNEL_ID", "0"))
CINEMA_CATEGORY_ID = int(os.getenv("CINEMA_CATEGORY_ID", "0"))

_ping = os.getenv("PING_ROLE_ID", "").strip()
PING_ROLE_ID = int(_ping) if _ping.isdigit() else None

CINEMA_DATA_FILE = os.getenv("CINEMA_DATA_FILE", "/app/data/cinemas.json")
