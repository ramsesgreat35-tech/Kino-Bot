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
        voice_channel = await create_cinema_voice(interaction, title, year_rating, meta, description, avatar_url)
        
        # Ссылка в виде кнопки
        class LinkView(discord.ui.View):
            def __init__(self):
                super().__init__()
                self.add_item(discord.ui.Button(
                    label="Зайти в войс", 
                    style=discord.ButtonStyle.link, 
                    url=f"https://discord.com/channels/{interaction.guild.id}/{voice_channel.id}",
                    emoji="🔊"
                ))

        await interaction.followup.send(
            f"✅ Кинотеатр создан! Нажми на кнопку ниже, чтобы зайти в свой канал.", 
            view=LinkView(), 
            ephemeral=True
        )
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

    # --- ТЕКСТ ДЛЯ ЛОГ-КАНАЛА (ТОЛЬКО СТАНДАРТНЫЕ ЭМОДЗИ) ---
    title_str = f"# 🍿 {title}"
    if year:
        title_str += f" (Фильм {year})"
    
    desc_str = ""
    if description:
        desc_str = f"> 📝 ** {description} **\n\n"
    
    current_time = int(time.time())

    text_content = (
        f"{title_str}\n"
        f"> [ОБНОВЛЕНО] Если ты видишь этот текст, значит код обновился!\n\n"
        f"{desc_str}"
        f"> 🎭 **Жанры:** {genre}\n"
        f"> ⭐ **Рейтинг:** {rating}   🔞 **Категория:** {age}   ⏱️ **Длительность:** {duration}\n\n"
        f"### 💖 **Проводит:** {owner.mention}\n"
        f"### 💖 **Место:**  {voice_channel.mention}\n"
        f"### 💖 **Время проведения:** <t:{current_time}:f>"
    )

    # 1. ОТПРАВЛЯЕМ В КАНАЛ ЛОГОВ
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(color=0x2ECC71, description=text_content)
        if avatar_url:
            log_embed.set_image(url=avatar_url)
        
        await log_channel.send(content=f"|| <@&{PING_ROLE_ID}> ||", embed=log_embed)

    # 2. ОТПРАВЛЯЕМ В ЧАТ ВОЙСА
    from control import CinemaPanelView
    view = CinemaPanelView(owner_id=owner.id, voice_id=voice_channel.id)
    
    panel_embed = discord.Embed(
        color=0x2ECC71,
        description=f"👑 Хост: {owner.mention}\n> Нажмите кнопку ниже, чтобы завершить просмотр."
    )
    
    await voice_channel.send(embed=panel_embed, view=view)

    # --- СОХРАНЯЕМ ---
    bot.cinemas[voice_channel.id] = {
        "voice_id": voice_channel.id,
        "owner_id": owner.id,
        "title": title,
    }
    bot.save_cinemas()

    return voice_channel

class CreateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(CreateCog(bot))
