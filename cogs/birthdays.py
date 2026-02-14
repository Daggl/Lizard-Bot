import json
import os
from discord.ext import commands, tasks
import discord
import datetime

DATA_FOLDER = "data"
BIRTHDAY_FILE = os.path.join(DATA_FOLDER, "birthdays.json")


def load_birthdays():
    try:
        with open(BIRTHDAY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_birthdays(data):
    with open(BIRTHDAY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


class Birthdays(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    @commands.command(name="geburtstag")
    async def geburtstag(self, ctx: commands.Context, datum: str):
        birthdays = load_birthdays()
        birthdays[str(ctx.author.id)] = datum
        save_birthdays(birthdays)
        await ctx.send(f"🎂 Geburtstag gespeichert: {datum}")

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        birthdays = load_birthdays()
        today = datetime.datetime.now().strftime("%d.%m")
        for user_id, date in birthdays.items():
            if date == today:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    channel = self.bot.get_channel(1471979381588230244)  # Ersetze durch die ID deines Kanals
                    if channel is not None:
                        await channel.send(f"🎉 Heute hat {user.mention} Geburtstag!")
                except Exception:
                    pass

    @check_birthdays.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Birthdays(bot))
