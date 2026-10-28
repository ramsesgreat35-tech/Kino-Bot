import re
import discord
from discord.ext import commands

from config import (
    CINEMA_CATEGORY_ID, PING_ROLE_ID, LOG_CHANNEL_ID, PINK,
)
from control import CinemaPanelView, build_panel_embed


# ---------- ПРОВЕРКИ (возвращают None, если значение не подходит) ----------
def check_year(val: str | None) -> str | None:
    if not val:
        return None
    try:
        y = int(val)
        if 1888 <= y <= 2100:
            return str(y)
    except ValueError:
        pass
    return None


def check_rating(val: str | None) -> str | None:
    if not val:
        return None
    try:
        r = float(val.replace(",", "."))
        if 0.0 <= r <= 10.0:
            return val.strip()
    except ValueError:
        pass
    return None


def check_text(val: str | None) -> str | None:
    if not val:
        return None
    val = val.strip()
    if not val or val.isdigit():
        return None
    return val


def split_parts(raw: str | None) -> list[str]:
    return [p.strip() for p in raw.split(",")] if raw else []


def quote(text: str) -> str:
    """Каждая строка — цитата '> ', чтобы блок не растягивался на всё сообщение."""
    return "\n".join(f"> {line}" if line.strip() else ">" for line in text.splitlines())


# ---------- ПОСТРОЕНИЕ ТРЁХ ЭМБЕДОВ ДЛЯ КАНАЛА ЛОГОВ ----------
def build_announce_embeds(
    *, owner, voice_channel, title, year, rating, genres, age, duration,
    description, avatar_url, timestamp,
) -> list[discord.Embed]:
    embeds: list[discord.Embed] = []

    # 1. Картинка (только если указана)
    if avatar_url:
        embeds.append(discord.Embed(color=PINK).set_image(url=avatar_url))

    # 2. Название + описание + жанры + рейтинг/категория/длительность
    head = f"# 🍿 {title}"
    if year:
        head += f" (Фильм {year})"
    blocks = [head]

    if description:
        blocks.append(quote(description))
    if genres:
        blocks.append(f"> 🎭 **Жанры:** {genres}")

    stats = []
    if rating:
        stats.append(f"⭐ **Рейтинг:** {rating}")
    if age:
        stats.append(f"🔞 **Категория:** {age}")
    if duration:
        stats.append(f"⏱️ **Длительность:** {duration}")
    if stats:
        blocks.append("> " + "   ".join(stats))

    # между блоками одна пустая строка, как на примере
    embeds.append(discord.Embed(color=PINK, description="\n\n".join(blocks)[:4096]))

    # 3. Кто проводит, где и когда
    embeds.append(discord.Embed(
        color=PINK,
        description=(
            f"### 💖 Проводит: {owner.mention}\n"
            f"### 🔊 Место: {voice_channel.mention}\n"
            f"### 🕒 Время проведения: <t:{timestamp}:f>"
        ),
    ))
    return embeds


async def process_cinema_creation(
    interaction: discord.Interaction,
    *,
    title: str, year_rating: str | None, meta: str | None,
    description: str | None, avatar_url: str | None,
):
    # Только люди с ролью кинотеатра
    if PING_ROLE_ID and not any(r.id == PING_ROLE_ID for r in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ У тебя нет роли для создания кинотеатра.", ephemeral=True
        )

    if avatar_url and not re.match(r"^https?://\S+$", avatar_url):
        avatar_url = None

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        voice_channel = await create_cinema_voice(
            interaction, title, year_rating, meta, description, avatar_url
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Зайти в войс", emoji="🔊", style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{interaction.guild.id}/{voice_channel.id}",
        ))
        await interaction.followup.send(
            "✅ Кинотеатр создан! Нажми на кнопку ниже, чтобы зайти в канал.",
            view=view, ephemeral=True,
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
    role = guild.get_role(PING_ROLE_ID) if PING_ROLE_ID else None

    # --- Войс-канал ---
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False, speak=False),
        owner: discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True,
            send_messages=True, manage_channels=True,
        ),
    }
    if role:
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True,
            send_messages=True, read_message_history=True,
        )
    else:
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True,
            send_messages=True, read_message_history=True,
        )

    voice_channel = await guild.create_voice_channel(
        name=f"🎬 {title}"[:100], category=category_ch, overwrites=overwrites, position=0,
    )

    # --- Разбор данных формы ---
    yr = split_parts(year_rating)
    year = check_year(yr[0] if len(yr) > 0 else None)
    rating = check_rating(yr[1] if len(yr) > 1 else None)

    # Жанров может быть несколько: всё, кроме последних двух полей, — жанры
    mt = split_parts(meta)
    if len(mt) >= 3:
        genres_raw, age_raw, dur_raw = ", ".join(mt[:-2]), mt[-2], mt[-1]
    else:
        genres_raw = mt[0] if len(mt) > 0 else None
        age_raw = mt[1] if len(mt) > 1 else None
        dur_raw = None
    genres = check_text(genres_raw)
    age = check_text(age_raw)
    duration = check_text(dur_raw)

    timestamp = int(discord.utils.utcnow().timestamp())

    # --- 1. Анонс в канал логов (3 эмбеда) ---
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        ping = f"|| <@&{PING_ROLE_ID}> ||" if PING_ROLE_ID else None
        kwargs = dict(
            owner=owner, voice_channel=voice_channel, title=title, year=year,
            rating=rating, genres=genres, age=age, duration=duration,
            description=description, timestamp=timestamp,
        )
        try:
            await log_channel.send(
                content=ping,
                embeds=build_announce_embeds(avatar_url=avatar_url, **kwargs),
            )
        except discord.HTTPException:
            # Если Discord не принял картинку — отправляем без неё
            await log_channel.send(
                content=ping,
                embeds=build_announce_embeds(avatar_url=None, **kwargs),
            )

    # --- 2. Панель в чат войса ---
    panel_embed = build_panel_embed(owner, title, timestamp, avatar_url)
    view = CinemaPanelView(owner_id=owner.id, voice_id=voice_channel.id)
    try:
        await voice_channel.send(embed=panel_embed, view=view)
    except discord.HTTPException:
        await voice_channel.send(embed=build_panel_embed(owner, title, timestamp, None), view=view)

    # --- Сохраняем ---
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
