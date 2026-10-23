import discord
from discord.ext import commands
from discord import app_commands

from config import PING_ROLE_ID


class CinemaControlView(discord.ui.View):
    def __init__(self, owner_id: int, voice_id: int, text_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.voice_id = voice_id
        self.text_id = text_id
        # уникальные custom_id на каждый кинотеатр
        self.start_show.custom_id = f"start_show:{voice_id}"
        self.close_cinema.custom_id = f"close_cinema:{voice_id}"

    @discord.ui.button(label="Начать показ", emoji="▶️", style=discord.ButtonStyle.primary)
    async def start_show(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "❌ Только создатель кинотеатра может запустить показ.", ephemeral=True
            )
        ping = f"<@&{PING_ROLE_ID}>" if PING_ROLE_ID else ""
        await interaction.response.send_message(
            f"🎬 **Показ начинается!** {ping}\n"
            f"Заходите в войс <#{self.voice_id}> — создатель включает демонстрацию экрана."
        )

    @discord.ui.button(label="Закрыть кинотеатр", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def close_cinema(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "❌ Только создатель может закрыть кинотеатр.", ephemeral=True
            )
        await interaction.response.send_message("🗑️ Кинотеатр закрывается...", ephemeral=True)

        bot: commands.Bot = interaction.client
        voice = interaction.guild.get_channel(self.voice_id)
        text = interaction.guild.get_channel(self.text_id)

        for ch in (voice, text):
            if ch:
                try:
                    await ch.delete()
                except discord.HTTPException:
                    pass

        bot.cinemas.pop(self.voice_id, None)
        bot.save_cinemas()


class ControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # восстанавливаем persistent views для сохранённых кинотеатров
        for voice_id, data in self.bot.cinemas.items():
            self.bot.add_view(CinemaControlView(
                owner_id=data["owner_id"],
                voice_id=voice_id,
                text_id=data["text_id"],
            ))

    @app_commands.command(name="close", description="Закрыть свой кинотеатр")
    async def close(self, interaction: discord.Interaction):
        bot: commands.Bot = interaction.client
        # ищем кинотеатр, где owner_id == interaction.user.id
        target = next(
            ((vid, d) for vid, d in bot.cinemas.items() if d["owner_id"] == interaction.user.id),
            None,
        )
        if target is None:
            return await interaction.response.send_message(
                "❌ У тебя нет активного кинотеатра.", ephemeral=True
            )

        voice_id, data = target
        voice = interaction.guild.get_channel(voice_id)
        text = interaction.guild.get_channel(data["text_id"])

        await interaction.response.send_message("🗑️ Твой кинотеатр закрывается...", ephemeral=True)

        for ch in (voice, text):
            if ch:
                try:
                    await ch.delete()
                except discord.HTTPException:
                    pass

        bot.cinemas.pop(voice_id, None)
        bot.save_cinemas()


async def setup(bot: commands.Bot):
    await bot.add_cog(ControlCog(bot))
