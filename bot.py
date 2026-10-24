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
        self.cinemas: dict[int, dict] = self._load_cinemas()

    def _load_cinemas(self) -> dict:
        if os.path.exists(CINEMA_DATA_FILE):
            try:
                with open(CINEMA_DATA_FILE, "r", encoding="utf-8") as f:
                    return {int(k): v for k, v in json.load(f).items()}
            except Exception:
                return {}
        return {}

    def save_cinemas(self):
        try:
            os.makedirs(os.path.dirname(CINEMA_DATA_FILE), exist_ok=True)
            with open(CINEMA_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.cinemas.items()}, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"⚠️ Ошибка сохранения: {e}")

    async def setup_hook(self):
        for ext in ["instruction", "create", "control"]:
            try:
                await self.load_extension(ext)
                print(f"✅ Модуль {ext} загружен")
            except Exception as e:
                print(f"❌ Ошибка загрузки {ext}: {e}")
        
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Команды синхронизированы")

    async def on_ready(self):
        print(f"✅ Бот запущен как {self.user}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and not after.channel:
            voice_id = before.channel.id
            if voice_id in self.cinemas:
                data = self.cinemas[voice_id]
                
                # Если вышел сам создатель
                if member.id == data["owner_id"]:
                    try:
                        await before.channel.delete()
                    except discord.HTTPException:
                        pass
                    
                    self.cinemas.pop(voice_id, None)
                    self.save_cinemas()

bot = CinemaBot()

if __name__ == "__main__":
    bot.run(TOKEN)
