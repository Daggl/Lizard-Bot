import discord
import json
import os

from discord.ext import commands


MIN_COUNT_FOR_RECORD = 150

COUNT_CHANNEL_ID = 1472258616164614266

DATA_FOLDER = "data"

DATA_FILE = os.path.join(DATA_FOLDER, "count.json")


# ---------- DATA ----------

def default_data():

    return {
        "current": 0,
        "last_user": None,
        "record": 0,
        "record_holder": None,
        "total_counts": {},
        "fails": 0
    }


def load():

    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    if not os.path.exists(DATA_FILE):
        save(default_data())

    try:

        with open(DATA_FILE, "r") as f:
            return json.load(f)

    except Exception:

        save(default_data())

        return default_data()


def save(data):

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------- COG ----------

class Count(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # ---------- COUNT SYSTEM ----------

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        if message.channel.id != COUNT_CHANNEL_ID:
            return

        data = load()

        try:

            number = int(message.content)

        except Exception:
            return

        expected = data["current"] + 1

        # SAME USER

        if str(message.author.id) == data["last_user"]:

            await message.add_reaction("❌")

            return

        # WRONG NUMBER

        if number != expected:

            await message.add_reaction("❌")

            await message.reply(
                f"💥 Error! Correct number would have been **{expected}**\n"
                f"🔄 Counter has been reset\n"
                f"🏆 Record: **{data['record']}**"
            )

            data["current"] = 0

            data["last_user"] = None

            data["fails"] += 1

            save(data)

            return

        # CORRECT

        await message.add_reaction("✅")

        data["current"] = number

        data["last_user"] = str(message.author.id)

        # USER STATS

        user = str(message.author.id)

        if user not in data["total_counts"]:
            data["total_counts"][user] = 0

        data["total_counts"][user] += 1

        # RECORD

        if number > data["record"] and number >= MIN_COUNT_FOR_RECORD:

            data["record"] = number

            data["record_holder"] = str(message.author.id)

            await message.channel.send(
                f"🏆 **NEW RECORD: {number}!**\n"
                f"👑 by {message.author.mention}"
            )

        save(data)

    # ---------- STATS ----------

    @commands.command()
    async def countstats(self, ctx):

        data = load()

        embed = discord.Embed(
            title="📊 Count Statistics",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Current",
            value=data["current"]
        )

        embed.add_field(
            name="Record",
            value=data["record"]
        )

        embed.add_field(
            name="Fails",
            value=data["fails"]
        )

        await ctx.send(embed=embed)

    # ---------- LEADERBOARD ----------

    @commands.command()
    async def counttop(self, ctx):

        data = load()

        sorted_users = sorted(
            data["total_counts"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        embed = discord.Embed(
            title="🏆 Count Leaderboard",
            color=discord.Color.gold()
        )

        text = ""

        for i, (user, amount) in enumerate(sorted_users, 1):

            member = ctx.guild.get_member(int(user))

            name = member.name if member else "Unknown"

            text += f"{i}. {name} — {amount}\n"

        embed.description = text

        await ctx.send(embed=embed)

    # ---------- ADMIN RESET ----------

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def countreset(self, ctx):

        save(default_data())

        await ctx.send("✅ Counter has been reset")


async def setup(bot):

    await bot.add_cog(Count(bot))
