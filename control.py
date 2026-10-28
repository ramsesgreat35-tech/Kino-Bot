import discord
from discord.ext import commands

from config import PINK


def build_panel_embed(
    owner: discord.abc.User,
    title: str,
    timestamp: int,
    poster_url: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        color=PINK,
        title=f"🎬 {title}",
        description=(
            f"### 👑 Хост: {owner.mention}\n"
            f"> 🕒 Начало: <t:{timestamp}:t>\n\n"
            "**💡 Подсказки**\n"
            "> 🖥️ Включи **демонстрацию экрана** в войсе\n"
            "> 🤫 Во время фильма соблюдайте тишину\n"
            "> 🗑️ Когда досмотрите — нажми кнопку ниже"
        ),
    )
    embed.set_thumbnail(url=owner.display_avatar.url)
    if poster_url:
        embed.set_image(url=poster_url)
    embed.set_footer(text="Панель управления кинотеатром • видна только хосту для действий")
    return embed


class ConfirmCloseView(discord.ui.View):
    def __init__(self, voice_id: int):
        super().__init__(timeout=30)
        self.voice_id = voice_id

    @discord.ui.button(label="Да, закрыть", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🌸 Кинотеатр закрывается...", view=None)

        bot: commands.Bot = interaction.client
        voice = interaction.guild.get_channel(self.voice_id)
        if voice:
            try:
                await voice.delete(reason="Кинотеатр закрыт хостом")
            except discord.HTTPException:
                pass

        bot.cinemas.pop(self.voice_id, None)
        bot.save_cinemas()

    @discord.ui.button(label="Отмена", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="👌 Отменено.", view=None)


class CinemaPanelView(discord.ui.View):
    def __init__(self, owner_id: int, voice_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.voice_id = voice_id
        self.close_cinema.custom_id = f"close_cinema:{voice_id}"

    @discord.ui.button(label="Закрыть кинотеатр", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def close_cinema(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "❌ Только хост может закрыть кинотеатр.", ephemeral=True
            )
        await interaction.response.send_message(
            "⚠️ Точно закрыть кинотеатр? Канал будет удалён.",
            view=ConfirmCloseView(self.voice_id),
            ephemeral=True,
        )


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
