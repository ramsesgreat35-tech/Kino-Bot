import discord
from discord.ext import commands
import re

from config import CINEMA_CATEGORY_ID, PING_ROLE_ID, LOG_CHANNEL_ID


async def process_cinema_creation(
    interaction: discord.Interaction,
    *,
    title: str, year: str | None, meta: str | None, 
    description: str | None, avatar_url: str | None,
):
    bot: commands.Bot = interaction.client

    if PING_ROLE_ID and not any(r.id == PING_ROLE_ID for r in interaction.user.roles):
        return await interaction.response.send_message("❌ У тебя нет роли для создания кинотеатра.", ephemeral=True)

    if avatar_url and not re.match(r"^https?://", avatar_url):
        avatar_url = None

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await create_cinema_voice(interaction, title, year, meta, description, avatar_url)
        await interaction.followup.send("✅ Кинотеатр создан! Заходи в войс.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: `{e}`", ephemeral=True)


async def create_cinema_voice(
    interaction: discord.Interaction,
    title: str, year: str | None, meta: str | None, 
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

    # --- КРАСИВЫЙ EMBED ---
    embed = discord.Embed(color=0x2ECC71)
    
    title_text = f"🍿 {title}"
    if year: title_text += f" ({year})"
    embed.title = title_text
    
    # Разбиваем строку "Комедия, 18+, 1ч 30м" на части
    meta_elements = []
    if meta:
        parts = [p.strip() for p in meta.split(",") if p.strip()]
        if len(parts) >= 1: meta_elements.append(f"🎭 **Жанр:** {parts[0]}")
        if len(parts) >= 2: meta_elements.append(f"🔞 **Возраст:** {parts[1]}")
        if len(parts) >= 3: meta_elements.append(f"⏱️ **Время:** {parts[2]}")
    
    # Блок с метаданными
    if meta_elements:
        embed.description = "\n".join(meta_elements) + "\n\n"
    else:
        embed.description = ""

    # Основное описание
    if description:
        embed.description += description
        
    if not embed.description:
        embed.description = "*Описание отсутствует.*"
    
    if avatar_url:
        embed.set_image(url=avatar_url)
        
    embed.set_footer(text=f"Организатор: {owner.display_name}", icon_url=owner.display_avatar.url if owner.display_avatar else None)
    
    await voice_channel.send(embed=embed)

    # --- Сохраняем ---
    bot.cinemas[voice_channel.id] = {
        "voice_id": voice_channel.id,
        "owner_id": owner.id,
        "title": title,
    }
    bot.save_cinemas()

    # --- Лог-канал ---
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(color=0x3498DB, title=f"🎬 Создан кинотеатр: {title}")
        log_desc = f"> **Организатор:** {owner.mention}\n> **Войс:** {voice_channel.mention}\n"
        if meta: log_desc += f"> **Инфо:** {meta}\n"
        log_embed.description = log_desc
        if avatar_url:
            log_embed.set_thumbnail(url=avatar_url)
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
