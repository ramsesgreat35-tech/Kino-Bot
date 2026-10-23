import discord
from discord.ext import commands

from create import create_cinema_channels


class AvatarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        pending = self.bot.pending_avatars.get(message.author.id)
        if not pending:
            return

        if not message.attachments:
            return await message.reply("❌ Нужно загрузить именно **картинку**.")

        att = message.attachments[0]
        if not (att.content_type or "").startswith("image/"):
            return await message.reply("❌ Это не картинка. Загрузи png/jpg/webp.")

        self.bot.pending_avatars.pop(message.author.id, None)

        # Fake interaction — только нужные поля
        class FakeInteraction:
            def __init__(self, user, guild, channel, client):
                self.user = user
                self.guild = guild
                self.channel = channel
                self.client = client

        fake = FakeInteraction(message.author, message.guild, message.channel, self.bot)

        try:
            await create_cinema_channels(
                fake,
                title=pending["title"],
                year=pending["year"],
                description=pending["description"],
                avatar_url=att.url,
            )
            await message.reply("✅ Кинотеатр создан!")
        except Exception as e:
            await message.reply(f"❌ Ошибка при создании: `{e}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(AvatarCog(bot))
