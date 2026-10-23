import discord
from discord.ext import commands
import re

from config import CINEMA_CATEGORY_ID, PING_ROLE_ID


async def process_cinema_creation(
    interaction: discord.Interaction,
    *,
    title: str,
    year: str,
    description: str,
    avatar_url: str | None,
):
    bot: commands.Bot = interaction.client

    # повторная проверка роли
    if PING_ROLE_ID and not any(r.id == PING_ROLE_ID for r in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ У тебя нет роли для создания кинотеатра.", ephemeral=True
        )

    if not avatar_url:
        await interaction.response.send_message(
            "🖼️ Ты не указал ссылку. **Загрузи аватарку файлом** в этот канал (2 минуты).",
            ephemeral=True,
        )
        bot.pending_avatars[interaction.user.id] = {
            "title": title, "year": year,
            "description": description,
            "channel_id": interaction.channel.id,
        }
        return

    if not re.match(r"^https?://", avatar_url):
        return await interaction.response.send_message(
            "❌ Ссылка на аватарку некорректна.", ephemeral=True
        )

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await create_cinema_channels(interaction, title, year, description, avatar_url)
        await interaction.followup.send("✅ Кинотеатр создан!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: `{e}`", ephemeral=True)


async def create_cinema_channels(
    interaction: discord.Interaction,
    title: str, year: str, description: str, avatar_url: str,
):
    guild = interaction.guild
    owner = interaction.user
    bot: commands.Bot = interaction.client

    category = discord.utils.get(guild.categories, id=CINEMA_CATEGORY_ID)
    if category is None:
        raise RuntimeError("Категория кинотеатров не найдена")

    role = guild.get_role(PING_ROLE_ID) if PING_ROLE_ID else None
    if role is None:
        raise RuntimeError("Роль для кинотеатра не найдена")

    # --- Войс ---
    voice_overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False, connect=False, speak=False
        ),
        role: discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True
        ),
        owner: discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True,
            mute_members=True, deafen_members=True, move_members=True,
            manage_channels=True, priority_speaker=True,
        ),
    }
    voice_channel = await guild.create_voice_channel(
        name=f"🎬 {title}"[:100],
        category=category, overwrites=voice_overwrites, position=0,
    )

    # --- Текст ---
    slug = re.sub(r"\s+", "-", title.lower())
    text_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        role: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
        owner: discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            read_message_history=True,
            manage_channels=True, manage_messages=True,
        ),
    }
    text_channel = await guild.create_text_channel(
        name=f"💬-{slug}"[:100],
        category=category, overwrites=text_overwrites, position=0,
    )

    # --- Embed с инфой ---
    embed = discord.Embed(
        color=0x2ECC71,
        title=f"🎬 {title} ({year})",
        description=description,
    )
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f"Создатель: {owner.display_name}")
    embed.timestamp = discord.utils.utcnow()

    # --- Кнопки ---
    from control import CinemaControlView
    view = CinemaControlView(owner_id=owner.id, voice_id=voice_channel.id, text_id=text_channel.id)
    await text_channel.send(embed=embed, view=view)

    # --- Сохранить ---
    bot.cinemas[voice_channel.id] = {
        "voice_id": voice_channel.id,
        "text_id": text_channel.id,
        "owner_id": owner.id,
        "title": title,
    }
    bot.save_cinemas()
    return voice_channel, text_channel


class CreateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(CreateCog(bot))
