import discord
from discord.ext import commands
import re

from config import CINEMA_CATEGORY_ID, PING_ROLE_ID, LOG_CHANNEL_ID


async def process_cinema_creation(
    interaction: discord.Interaction,
    *,
    title: str,
    year: str | None,
    extra_info: str | None,
    description: str | None,
    avatar_url: str | None,
):
    bot: commands.Bot = interaction.client

    if PING_ROLE_ID and not any(r.id == PING_ROLE_ID for r in interaction.user.roles):
        return await interaction.response.send_message("❌ У тебя нет роли для создания кинотеатра.", ephemeral=True)

    if avatar_url and not re.match(r"^https?://", avatar_url):
        avatar_url = None

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await create_cinema_channels(
            interaction, title, year, extra_info, description, avatar_url
        )
        await interaction.followup.send("✅ Кинотеатр создан!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: `{e}`", ephemeral=True)


async def create_cinema_channels(
    interaction: discord.Interaction,
    title: str, year: str | None, extra_info: str | None, 
    description: str | None, avatar_url: str | None,
):
    guild = interaction.guild
    owner = interaction.user
    bot: commands.Bot = interaction.client

    category_ch = discord.utils.get(guild.categories, id=CINEMA_CATEGORY_ID)
    role = guild.get_role(PING_ROLE_ID) if PING_ROLE_ID else guild.default_role

    # --- Войс ---
    voice_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False, speak=False),
        role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
        owner: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, mute_members=True, deafen_members=True, move_members=True, manage_channels=True),
    }
    voice_channel = await guild.create_voice_channel(name=f"🎬 {title}"[:100], category=category_ch, overwrites=voice_overwrites, position=0)

    # --- Текст ---
    slug = re.sub(r"\s+", "-", title.lower())
    text_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        owner: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    text_channel = await guild.create_text_channel(name=f"💬-{slug}"[:100], category=category_ch, overwrites=text_overwrites, position=0)

    # --- КРАСИВЫЙ EMBED ---
    embed = discord.Embed(color=0x2ECC71)
    
    # Заголовок (с годом, если он есть)
    title_text = f"🍿 {title}"
    if year:
        title_text += f" ({year})"
    embed.title = title_text
    
    desc_text = ""
    if extra_info:
        desc_text += f"> **Инфо:** {extra_info}\n\n"
    if description:
        desc_text += f"{description}"
    
    if desc_text:
        embed.description = desc_text
    else:
        embed.description = "*Описание не указано.*"
    
    if avatar_url:
        embed.set_image(url=avatar_url)
        
    embed.set_footer(text=f"Создатель: {owner.display_name}", icon_url=owner.display_avatar.url if owner.display_avatar else None)
    
    await text_channel.send(embed=embed)

    # --- Сохраняем ---
    bot.cinemas[voice_channel.id] = {
        "voice_id": voice_channel.id,
        "text_id": text_channel.id,
        "owner_id": owner.id,
        "title": title,
    }
    bot.save_cinemas()

    # --- Лог-канал ---
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(color=0x3498DB, title=f"🎬 Создан кинотеатр: {title}")
        log_desc = f"> **Создатель:** {owner.mention}\n> **Войс:** {voice_channel.mention}\n"
        if year: log_desc += f"> **Год:** {year}\n"
        if extra_info: log_desc += f"> **Инфо:** {extra_info}\n"
        
        log_embed.description = log_desc
        if avatar_url:
            log_embed.set_thumbnail(url=avatar_url)
        await log_channel.send(embed=log_embed)

    # --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
    from control import CinemaPanelView
    view = CinemaPanelView(owner_id=owner.id, voice_id=voice_channel.id, text_id=text_channel.id)
    
    panel_embed = discord.Embed(
        color=0xE74C3C,
        description=f"👑 {owner.mention}, панель управления кинотеатром.\n> Нажмите на кнопку ниже, чтобы удалить канал."
    )
    
    await text_channel.send(embed=panel_embed, view=view)

    return voice_channel, text_channel


class CreateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(CreateCog(bot))
