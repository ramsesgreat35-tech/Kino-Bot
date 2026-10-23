import discord
from discord.ext import commands
from discord import app_commands

from config import INSTRUCTION_CHANNEL_ID, PING_ROLE_ID


class CreateCinemaModal(discord.ui.Modal, title="🎬 Создание кинотеатра"):
    title_input = discord.ui.TextInput(
        label="Название фильма/аниме/мультика",
        max_length=80, required=True,
    )
    year_input = discord.ui.TextInput(
        label="Год", max_length=4, required=True,
    )
    description_input = discord.ui.TextInput(
        label="Описание", style=discord.TextStyle.paragraph,
        max_length=500, required=True,
    )
    avatar_input = discord.ui.TextInput(
        label="Ссылка на аватарку (или оставь пустым)",
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from create import process_cinema_creation
        await process_cinema_creation(
            interaction,
            title=self.title_input.value.strip(),
            year=self.year_input.value.strip(),
            description=self.description_input.value.strip(),
            avatar_url=self.avatar_input.value.strip() or None,
        )


class CreateButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Создать кинотеатр", emoji="🎬",
        style=discord.ButtonStyle.success,
        custom_id="create_cinema_btn",
    )
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверка роли
        if PING_ROLE_ID and not any(r.id == PING_ROLE_ID for r in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ У тебя нет роли для создания кинотеатра.", ephemeral=True
            )
        await interaction.response.send_modal(CreateCinemaModal())


class InstructionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Отправить инструкцию в канал кинотеатра")
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
        title="🎬 Добро пожаловать в Кинотеатр",
        description=(
            "**Как пользоваться ботом:**\n\n"
            "1️⃣ Нажми кнопку **«Создать кинотеатр»** ниже (только с ролью).\n"
            "2️⃣ Заполни форму: название, год, описание, аватарку.\n"
            "3️⃣ Бот автоматически создаст войс и текстовый канал.\n"
            "4️⃣ Создатель нажимает **▶️ Начать показ** — бот пингует роль.\n"
            "5️⃣ Включи демонстрацию экрана в войсе — и смотрите!\n\n"
            "**Правила:**\n"
            "📜 Только создатель управляет каналом (мут/кик/показ).\n"
            "🔇 Во время фильма — тишина. Нарушил → мут/кик.\n"
            "🤝 Уважение обязательно. Спам/оскорбления — бан.\n"
            "🎞️ Один кинотеатр = один фильм.\n"
            "🖼️ Аватарка и описание — по теме."
        ),
    )
    embed.set_footer(text="Приятного просмотра!")
    await channel.send(embed=embed, view=CreateButton())


async def setup(bot: commands.Bot):
    await bot.add_cog(InstructionCog(bot))
