import discord
from discord.ext import commands
from discord import app_commands

from config import INSTRUCTION_CHANNEL_ID, PING_ROLE_ID

class CreateCinemaModal(discord.ui.Modal, title="🎬 Создание кинотеатра"):
    title_input = discord.ui.TextInput(label="Название", max_length=80, required=True)
    year_input = discord.ui.TextInput(label="Год", max_length=4, required=False)
    # Объединили Жанр, Возраст и Время в одно поле
    meta_input = discord.ui.TextInput(label="Жанр, Возраст, Длительность", placeholder="Комедия, 18+, 1ч 30м", max_length=100, required=False)
    description_input = discord.ui.TextInput(label="Описание", style=discord.TextStyle.paragraph, max_length=500, required=False)
    avatar_input = discord.ui.TextInput(label="Ссылка на аватарку", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        from create import process_cinema_creation
        await process_cinema_creation(
            interaction,
            title=self.title_input.value.strip(),
            year=self.year_input.value.strip() if self.year_input.value else None,
            meta=self.meta_input.value.strip() if self.meta_input.value else None,
            description=self.description_input.value.strip() if self.description_input.value else None,
            avatar_url=self.avatar_input.value.strip() if self.avatar_input.value else None,
        )

class CreateButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Создать кинотеатр", emoji="🎬", style=discord.ButtonStyle.success, custom_id="create_cinema_btn")
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if PING_ROLE_ID and not any(r.id == PING_ROLE_ID for r in interaction.user.roles):
            return await interaction.response.send_message("❌ У вас нет роли для создания кинотеатра.", ephemeral=True)
        await interaction.response.send_modal(CreateCinemaModal())

class InstructionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Отправить инструкцию в канал")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        channel = self.bot.get_channel(INSTRUCTION_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message("❌ Канал не найден.", ephemeral=True)
        await send_instruction(channel)
        await interaction.response.send_message("✅ Инструкция отправлена.", ephemeral=True)

async def send_instruction(channel: discord.TextChannel):
    embed = discord.Embed(
        color=0x2ECC71,
        title="🍿 Добро пожаловать в Кинотеатр!",
        description=(
            "Создайте свой собственный кинотеатр за пару секунд.\n\n"
            "**📌 Как это работает:**\n"
            "> 1️⃣ Нажмите кнопку **«Создать кинотеатр»** ниже.\n"
            "> 2️⃣ Заполните форму (многое можно пропустить).\n"
            "> 3️⃣ Бот создаст голосовой канал.\n"
            "> 4️⃣ Заходите в войс и включайте демонстрацию экрана!\n\n"
            "**📜 Правила:**\n"
            "> 👑 Создатель управляет каналом.\n"
            "> 🤫 Во время фильма соблюдайте тишину.\n"
            "> 🤝 Уважайте друг друга."
        ),
    )
    await channel.send(embed=embed, view=CreateButton())

async def setup(bot: commands.Bot):
    await bot.add_cog(InstructionCog(bot))
