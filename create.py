import discord
from discord.ext import commands
import re
import time

from config import CINEMA_CATEGORY_ID, PING_ROLE_ID, LOG_CHANNEL_ID

async def process_cinema_creation(
    interaction: discord.Interaction,
    *,
    title: str, year_rating: str | None, meta: str | None, 
    description: str | None, avatar_url: str | None,
):
    bot: commands.Bot = interaction.client

    if PING_ROLE_ID and not any(r.id == PING_ROLE_ID for r in interaction.user.roles):
        return await interaction.response.send_message("❌ У тебя нет роли для создания кинотеатра.", ephemeral=True)

    if avatar_url and not re.match(r"^https?://", avatar_url):
        avatar_url = None

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await create_cinema_voice(interaction, title, year_rating, meta, description, avatar_url)
        await interaction.followup.send("✅ Кинотеатр создан! Заходи в войс.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: `{e}`", ephemeral=True)

async def create_cinema_voice(
    interaction: discord.Interaction,
    title: str, year_rating: str | None, meta: str | None, 
    description: str | None, avatar_url: str | None,
):
    guild = interaction.guild
    owner = interaction.user
    bot: commands.Bot = interaction.client

    category_ch = discord.utils.get(guild.categories, id=CINEMA_CATEGORY_ID)
    role = guild.get_role(PING_ROLE_ID) if PING_ROLE_ID else guild.default_role

    # --- Создаем Войс-канал ---
    voice_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False, speak=False),
        role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, send_messages=True, read_message_history=True),
        owner: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, send_messages=True, manage_channels=True),
    }
    voice_channel = await guild.create_voice_channel(name=f"🎬 {title}"[:100], category=category_ch, overwrites=voice_overwrites, position=0)

    # --- РАЗБИРАЕМ ДАННЫЕ ---
    year, rating = "", "-"
    if year_rating:
        parts = [p.strip() for p in year_rating.split(",")]
        year = parts[0] if len(parts) > 0 else ""
        rating = parts[1] if len(parts) > 1 else "-"

    genre, age, duration = "-", "-", "-"
    if meta:
        parts = [p.strip() for p in meta.split(",")]
        genre = parts[0] if len(parts) > 0 else "-"
        age = parts[1] if len(parts) > 1 else "-"
        duration = parts[2] if len(parts) > 2 else "-"

    # --- 1 ЭМБЕД: ТОЛЬКО КАРТИНКА ---
    if avatar_url:
        embed_img = discord.Embed(color=0x2ECC71)
        embed_img.set_image(url=avatar_url)
        await voice_channel.send(embed=embed_img)

    # --- 2 ЭМБЕД: ТЕКСТ ---
    title_str = f"# <:emoji_2:1544441724225720350>{title}"
    if year:
        title_str += f" (Фильм {year})"
    
    desc_str = ""
    if description:
        desc_str = f"> <:emoji_3:1549860670932254840>** {description} **\n"
    
    # Формируем строку с временем
    current_time = int(time.time())

    text_content = (
        f"{title_str}\n"
        f"{desc_str}"
        f"> **<:emoji_6:1553507905561432115>Жанры: **{genre}\n"
        f"> **<:emoji_5:1544441995412373595>Рейтинг:** {rating}   **<:emoji_4:1544432963243221073>Категория:** {age}   **<:emoji_1:1549861320810307604>Длительность:** {duration}\n"
        f"### <a:hearts_pink:1521120519003443270>**Проводит:** {owner.mention}\n"
        f"### <a:hearts_pink:1521120519003443270>**Место:**  {voice_channel.mention}\n"
        f"### <a:hearts_pink:1521120519003443270>**Время проведения:** <t:{current_time}:f>"
    )
    
    embed_text = discord.Embed(color=0x2ECC71, description=text_content)
    
    # Отправляем скрытый пинг отдельно от эмбеда, чтобы не ломался Markdown
    await voice_channel.send(content=f"|| <@&{PING_ROLE_ID}> ||", embed=embed_text)

    # --- СОХРАНЯЕМ ---
    bot.cinemas[voice_channel.id] = {
        "voice_id": voice_channel.id,
        "owner_id": owner.id,
        "title": title,
    }
    bot.save_cinemas()

    # --- ЛОГ-КАНАЛ ---
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(color=0x2ECC71, description=text_content)
        await log_channel.send(embed=log_embed)

    # --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
    from control import CinemaPanelView
    view = CinemaPanelView(owner_id=owner.id, voice_id=voice_channel.id)
    
    panel_embed = discord.Embed(
        color=0x2ECC71,
        description=f"👑 {owner.mention}, управление показом.\n> Нажмите кнопку ниже, чтобы закрыть кинотеатр."
    )
    
    await voice_channel.send(embed=panel_embed, view=view)

    return voice_channel

class CreateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(CreateCog(bot))
