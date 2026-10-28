import discord
from discord.ext import commands
from discord import app_commands

from banner_data import banner_file
from config import INSTRUCTION_CHANNEL_ID, PING_ROLE_ID, PINK
from control import find_user_cinema


def has_cinema_role(member: discord.abc.User) -> bool:
    """Создавать кинотеатр могут только люди с ролью кинотеатра."""
    if not PING_ROLE_ID:
        return True
    roles = getattr(member, "roles", [])
    return any(r.id == PING_ROLE_ID for r in roles)


class CreateCinemaModal(discord.ui.Modal, title="🎬 Создание кинотеатра"):
    title_input = discord.ui.TextInput(
        label="Название", placeholder="1+1", max_length=80, required=True
    )
    year_rating_input = discord.ui.TextInput(
        label="Год, Рейтинг", placeholder="2011, 9.4", max_length=20, required=False
    )
    meta_input = discord.ui.TextInput(
        label="Жанр, Возраст, Длительность",
        placeholder="Драма, Комедия, 18+, 107 мин.",
        max_length=100, required=False,
    )
    description_input = discord.ui.TextInput(
        label="Описание", style=discord.TextStyle.paragraph,
        max_length=1000, required=False,
    )
    avatar_input = discord.ui.TextInput(
        label="Ссылка на картинку (постер)", placeholder="https://...",
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from create import process_cinema_creation
        await process_cinema_creation(
            interaction,
            title=self.title_input.value.strip(),
            year_rating=self.year_rating_input.value.strip() or None,
            meta=self.meta_input.value.strip() or None,
            description=self.description_input.value.strip() or None,
            avatar_url=self.avatar_input.value.strip() or None,
        )


class CreateButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Создать кинотеатр", emoji="🎬",
        style=discord.ButtonStyle.primary, custom_id="create_cinema_btn",
    )
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_cinema_role(interaction.user):
            return await interaction.response.send_message(
                "❌ У вас нет роли для создания кинотеатра.", ephemeral=True
            )
        existing = find_user_cinema(interaction.client, interaction.guild, interaction.user.id)
        if existing:
            return await interaction.response.send_message(
                f"❌ У тебя уже есть открытый кинотеатр: {existing.mention}\n"
                "Закрой его, чтобы создать новый.",
                ephemeral=True,
            )
        await interaction.response.send_modal(CreateCinemaModal())


class InstructionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Чтобы кнопка работала и после перезапуска бота
        self.bot.add_view(CreateButton())

    @app_commands.command(name="setup", description="Отправить панель создания кинотеатра в канал")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        channel = self.bot.get_channel(INSTRUCTION_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message("❌ Канал не найден.", ephemeral=True)
        await send_instruction(channel)
        await interaction.response.send_message("✅ Панель отправлена.", ephemeral=True)


async def send_instruction(channel: discord.TextChannel):
    description = (
        "Создай свой уютный кинотеатр за пару секунд 💞\n\n"
        "### 📌 Как это работает\n"
        "> 1️⃣ Нажми кнопку **«Создать кинотеатр»** ниже\n"
        "> 2️⃣ Заполни форму — почти всё можно пропустить\n"
        "> 3️⃣ Бот создаст голосовой канал и анонсирует сеанс\n"
        "> 4️⃣ Заходи в войс и включай демонстрацию экрана 🍿\n\n"
        "### 📜 Правила\n"
        "> 👑 Создатель управляет своим кинотеатром\n"
        "> 🤫 Во время фильма соблюдай тишину\n"
        "> 🌸 Уважай других зрителей"
    )
    embed = discord.Embed(color=PINK, description=description)
    embed.set_image(url="attachment://banner.png")
    embed.set_footer(text="Создавать кинотеатр могут только участники с ролью кинотеатра")

    await channel.send(embed=embed, file=banner_file("banner.png"), view=CreateButton())


async def setup(bot: commands.Bot):
    await bot.add_cog(InstructionCog(bot))
