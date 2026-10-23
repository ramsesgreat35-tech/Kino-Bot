import discord
from discord.ext import commands
import json
import os

from config import TOKEN, CINEMA_DATA_FILE, GUILD_ID

class CinemaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)
        self.pending_avatars: dict[int, dict] = {}
        self.cinemas: dict[int, dict] = self._load_cinemas()

    def _load_cinemas(self) -> dict:
        if os.path.exists(CINEMA_DATA_FILE):
            try:
                with open(CINEMA_DATA_FILE, "r", encoding="utf-8") as f:
                    return {int(k): v for k, v in json.load(f).items()}
            except (json.JSONDecodeError, ValueError):
                print("⚠️ cinemas.json повреждён — начинаем с пустого.")
                return {}
        return {}

    def save_cinemas(self):
        try:
            # Убедимся, что папка существует (на всякий случай)
            os.makedirs(os.path.dirname(CINEMA_DATA_FILE), exist_ok=True)
            with open(CINEMA_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {str(k): v for k, v in self.cinemas.items()},
                    f, ensure_ascii=False, indent=2,
                )
        except OSError as e:
            print(f"⚠️ Не удалось сохранить cinemas.json: {e}")

    async def setup_hook(self):
        # Загружаем модули из корня (без префикса cogs.)
        for ext in ["instruction", "create", "control", "avatar"]:
            try:
                await self.load_extension(ext)
                print(f"✅ Модуль {ext} загружен")
            except Exception as e:
                print(f"❌ Ошибка загрузки {ext}: {e}")
        
        # Синхронизация команд
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Slash-команды синхронизированы")

    async def on_ready(self):
        print(f"✅ Бот запущен как {self.user} (id: {self.user.id})")

bot = CinemaBot()

if __name__ == "__main__":
    bot.run(TOKEN)
