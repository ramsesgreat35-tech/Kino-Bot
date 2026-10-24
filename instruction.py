import discord
from discord.ext import commands
from discord import app_commands

from config import INSTRUCTION_CHANNEL_ID, PING_ROLE_ID

# --- ВТОРАЯ МОДАЛКА (Детали) ---
class CinemaDetailsModal(discord.ui.Modal, title="🎬 Детали фильма (Шаг 2/2)"):
    genre_input = discord.ui.TextInput(label="Жанр (например, Комедия)", max_length=50, required=False)
    category_input = discord.ui.TextInput(label="Возраст (например, 18+)", max_length=10, required=False)
    duration_input = discord.ui.TextInput(label="Длительность (например, 1ч 30м)", max_length=20, required=False)
    avatar_input = discord.ui.TextInput(label="Ссылка на аватарку", required=False)

    def __init__(self, title: str, year: str, description: str):
        super().__init__()
        # Сохраняем данные из первой модалки
        self.c_title = title
        self.c_year = year
        self.c_desc = description

    async def on_submit(self, interaction: discord.Interaction):
        from create import process_cinema_creation
        await process_cinema_creation(
            interaction,
            title=self.c_title,
            year=self.c_year,
            genre=self.genre_input.value.strip() if self.genre_input.value else None,
            category=self.category_input.value.strip() if self.category_input.value else None,
            duration=self.duration_input.value.strip() if self.duration_input.value else None,
            description=self.c_desc,
            avatar_url=self.avatar_input.value.strip() if self.avatar_input.value else None,
        )

# --- ПЕРВАЯ МОДАЛКА (Основное) ---
class CreateCinemaModal(discord.ui.Modal, title="🎬 Создание кинотеатра (Шаг 1/2)"):
    title_input = discord.ui.TextInput(label="Название фильма/аниме", max_length=80, required=True)
    year_input = discord.ui.TextInput(label="Год (необязательно)", max_length=4, required=False)
    description_input = discord.ui.TextInput(label="Описание (необязательно)", style=discord.TextStyle.paragraph, max_length=500, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Вызываем вторую модалку, передавая данные
        await interaction.response.send_modal(
            CinemaDetailsModal(
                title=self.title_input.value.strip(),
                year=self.year_input.value.strip(),
                description=self.description_input.value.strip()
            )
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
