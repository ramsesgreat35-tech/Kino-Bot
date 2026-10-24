import discord
from discord.ext import commands

class CinemaPanelView(discord.ui.View):
    def __init__(self, owner_id: int, voice_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.voice_id = voice_id
        
        self.close_cinema.custom_id = f"close_cinema:{voice_id}"

    @discord.ui.button(label="Закрыть кинотеатр", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def close_cinema(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("❌ Только создатель может закрыть кинотеатр.", ephemeral=True)
        
        await interaction.response.send_message("🗑️ Кинотеатр закрывается...", ephemeral=True)

        bot: commands.Bot = interaction.client
        voice = interaction.guild.get_channel(self.voice_id)

        if voice:
            try:
                await voice.delete()
            except discord.HTTPException:
                pass

        bot.cinemas.pop(self.voice_id, None)
        bot.save_cinemas()

class ControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        for voice_id, data in self.bot.cinemas.items():
            self.bot.add_view(CinemaPanelView(
                owner_id=data["owner_id"],
                voice_id=voice_id,
            ))

async def setup(bot: commands.Bot):
    await bot.add_cog(ControlCog(bot))
