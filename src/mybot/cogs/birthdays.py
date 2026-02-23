import datetime
import os

from discord.ext import commands, tasks

from mybot.utils.jsonstore import safe_load_json, safe_save_json

DATA_FOLDER = "data"
BIRTHDAY_FILE = os.path.join(DATA_FOLDER, "birthdays.json")


def load_birthdays():
    return safe_load_json(BIRTHDAY_FILE, default={})


def save_birthdays(data):
    safe_save_json(BIRTHDAY_FILE, data)


class Birthdays(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    @commands.command(name="birthday")
    async def birthday(self, ctx: commands.Context, date: str):

        birthdays = load_birthdays()

        birthdays[str(ctx.author.id)] = date

        save_birthdays(birthdays)

        await ctx.send(f"🎂 Birthday saved: {date}")

    @tasks.loop(hours=24)
    async def check_birthdays(self):

        birthdays = load_birthdays()

        today = datetime.datetime.now().strftime("%d.%m")

        for user_id, date in birthdays.items():

            if date == today:

                try:

                    user = await self.bot.fetch_user(int(user_id))

                    channel = self.bot.get_channel(1471979381588230244)

                    if channel is not None:

                        await channel.send(f"🎉 Today is {user.mention}'s birthday!")

                except Exception:
                    pass

    @check_birthdays.before_loop
    async def before_check(self):

        await self.bot.wait_until_ready()


async def setup(bot):

    await bot.add_cog(Birthdays(bot))
