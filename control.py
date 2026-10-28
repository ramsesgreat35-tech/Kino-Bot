import asyncio
import time

import discord
from discord.ext import commands

from config import PINK

# Сколько ждём возвращения хоста, прежде чем удалить кинотеатр
GRACE_SECONDS = 60


def find_user_cinema(bot: commands.Bot, guild: discord.Guild, user_id: int):
    """Возвращает открытый кинотеатр пользователя (канал) или None.
    Заодно чистит записи о каналах, которых уже не существует."""
    changed = False
    found = None
    for voice_id, data in list(bot.cinemas.items()):
        if data.get("owner_id") != user_id:
            continue
        channel = guild.get_channel(voice_id)
        if channel:
            found = channel
        else:
            bot.cinemas.pop(voice_id, None)
            changed = True
    if changed:
        bot.save_cinemas()
    return found


def build_panel_embed(
    owner: discord.abc.User,
    title: str,
    timestamp: int,
    poster_filename: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        color=PINK,
        title=f"🎬 {title}",
        description=(
            f"### 👑 Хост: {owner.mention}\n"
            f"> 🕒 Начало: <t:{timestamp}:t>\n\n"
            "**💡 Подсказки**\n"
            "> 🖥️ Включи **демонстрацию экрана** в войсе\n"
            "> 🤫 Во время фильма соблюдайте тишину\n"
            f"> ⏳ Если хост выйдет из канала и не вернётся за {GRACE_SECONDS} сек., кинотеатр закроется\n"
            "> 🗑️ Когда досмотрите — нажми кнопку ниже"
        ),
    )
    embed.set_thumbnail(url=owner.display_avatar.url)
    if poster_filename:
        embed.set_image(url=f"attachment://{poster_filename}")
    embed.set_footer(text="Панель управления кинотеатром")
    return embed


class ConfirmCloseView(discord.ui.View):
    def __init__(self, voice_id: int):
        super().__init__(timeout=30)
        self.voice_id = voice_id

    @discord.ui.button(label="Да, закрыть", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🌸 Кинотеатр закрывается...", view=None)

        bot: commands.Bot = interaction.client
        voice = interaction.guild.get_channel(self.voice_id)
        if voice:
            try:
                await voice.delete(reason="Кинотеатр закрыт хостом")
            except discord.HTTPException:
                pass

        bot.cinemas.pop(self.voice_id, None)
        bot.save_cinemas()

    @discord.ui.button(label="Отмена", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="👌 Отменено.", view=None)


class CinemaPanelView(discord.ui.View):
    def __init__(self, owner_id: int, voice_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.voice_id = voice_id
        self.close_cinema.custom_id = f"close_cinema:{voice_id}"

    @discord.ui.button(label="Закрыть кинотеатр", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def close_cinema(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "❌ Только хост может закрыть кинотеатр.", ephemeral=True
            )
        await interaction.response.send_message(
            "⚠️ Точно закрыть кинотеатр? Канал будет удалён.",
            view=ConfirmCloseView(self.voice_id),
            ephemeral=True,
        )


class ControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timers: dict[int, asyncio.Task] = {}
        self.notices: dict[int, discord.Message] = {}

    async def cog_load(self):
        for voice_id, data in self.bot.cinemas.items():
            self.bot.add_view(CinemaPanelView(owner_id=data["owner_id"], voice_id=voice_id))

    async def cog_unload(self):
        for task in self.timers.values():
            task.cancel()
        self.timers.clear()

    # ---------- хост вышел / вернулся ----------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return  # мут/размут/стрим — не интересует

        # Хост покинул свой кинотеатр -> запускаем минуту ожидания
        if before.channel and before.channel.id in self.bot.cinemas:
            if member.id == self.bot.cinemas[before.channel.id]["owner_id"]:
                self._start_timer(before.channel)

        # Хост вернулся -> отменяем удаление
        if after.channel and after.channel.id in self.bot.cinemas:
            if member.id == self.bot.cinemas[after.channel.id]["owner_id"]:
                await self._cancel_timer(after.channel.id)

    def _start_timer(self, channel: discord.VoiceChannel):
        if channel.id in self.timers:
            return
        self.timers[channel.id] = asyncio.create_task(self._countdown(channel))

    async def _cancel_timer(self, voice_id: int):
        task = self.timers.pop(voice_id, None)
        if task:
            task.cancel()
        notice = self.notices.pop(voice_id, None)
        if notice:
            try:
                await notice.delete()
            except discord.HTTPException:
                pass

    async def _countdown(self, channel: discord.VoiceChannel):
        voice_id = channel.id
        deadline = int(time.time()) + GRACE_SECONDS
        try:
            try:
                self.notices[voice_id] = await channel.send(
                    f"⏳ Хост вышел из канала. Если он не вернётся <t:{deadline}:R>, кинотеатр будет закрыт."
                )
            except discord.HTTPException:
                pass

            await asyncio.sleep(GRACE_SECONDS)

            # Убираем себя из словаря заранее, чтобы удаление канала не отменило эту задачу
            self.timers.pop(voice_id, None)

            data = self.bot.cinemas.get(voice_id)
            voice = self.bot.get_channel(voice_id)
            if voice and data and any(m.id == data["owner_id"] for m in voice.members):
                return  # на всякий случай: хост уже в канале

            if voice:
                try:
                    await voice.delete(reason="Хост не вернулся в течение минуты")
                except discord.HTTPException:
                    pass
            self.bot.cinemas.pop(voice_id, None)
            self.bot.save_cinemas()
        finally:
            if self.timers.get(voice_id) is asyncio.current_task():
                self.timers.pop(voice_id, None)
            self.notices.pop(voice_id, None)

    # ---------- канал удалён (вручную или ботом) ----------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if channel.id in self.bot.cinemas:
            self.bot.cinemas.pop(channel.id, None)
            self.bot.save_cinemas()
        task = self.timers.pop(channel.id, None)
        if task:
            task.cancel()
        self.notices.pop(channel.id, None)


async def setup(bot: commands.Bot):
    await bot.add_cog(ControlCog(bot))
