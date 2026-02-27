import os

import discord
from discord import app_commands
from discord.ext import commands

from mybot.utils.config import load_cog_config
from mybot.utils.jsonstore import safe_load_json, safe_save_json


def _cfg() -> dict:
    try:
        return load_cog_config("count") or {}
    except Exception:
        return {}


def _count_channel_id():
    try:
        raw = _cfg().get("COUNT_CHANNEL_ID", None)
        return int(raw) if raw is not None else None
    except Exception:
        return None


def _min_count_for_record() -> int:
    try:
        return int(_cfg().get("MIN_COUNT_FOR_RECORD", 150) or 150)
    except Exception:
        return 150


def _data_paths() -> tuple[str, str]:
    cfg = _cfg()
    folder = str(cfg.get("DATA_FOLDER", "data") or "data")
    file_name = str(cfg.get("DATA_FILE", "count.json") or "count.json")
    return folder, os.path.join(folder, file_name)


def default_data():

    return {
        "current": 0,
        "last_user": None,
        "record": 0,
        "record_holder": None,
        "total_counts": {},
        "fails": 0,
    }


def load():
    data_folder, data_file = _data_paths()

    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    if not os.path.exists(data_file):
        save(default_data())
    return safe_load_json(data_file, default=default_data())


def save(data):
    _, data_file = _data_paths()
    safe_save_json(data_file, data)


class Count(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        count_channel_id = _count_channel_id()
        if count_channel_id and message.channel.id != count_channel_id:
            return

        data = load()

        try:

            number = int(message.content)

        except Exception:
            return

        expected = data["current"] + 1

        if str(message.author.id) == data["last_user"]:

            await message.add_reaction("❌")

            return

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

        await message.add_reaction("✅")

        data["current"] = number

        data["last_user"] = str(message.author.id)

        user = str(message.author.id)

        if user not in data["total_counts"]:
            data["total_counts"][user] = 0

        data["total_counts"][user] += 1

        min_count_for_record = _min_count_for_record()
        if number > data["record"] and number >= min_count_for_record:

            data["record"] = number

            data["record_holder"] = str(message.author.id)

            await message.channel.send(
                f"🏆 **NEW RECORD: {number}!**\n" f"👑 by {message.author.mention}"
            )

        save(data)

    @commands.hybrid_command(description="Countstats command.")
    async def countstats(self, ctx):

        data = load()

        embed = discord.Embed(title="📊 Count Statistics", color=discord.Color.blue())

        embed.add_field(name="Current", value=data["current"])

        embed.add_field(name="Record", value=data["record"])

        embed.add_field(name="Fails", value=data["fails"])

        await ctx.send(embed=embed)

    @commands.hybrid_command(description="Counttop command.")
    async def counttop(self, ctx):

        data = load()

        sorted_users = sorted(
            data["total_counts"].items(), key=lambda x: x[1], reverse=True
        )[:10]

        embed = discord.Embed(title="🏆 Count Leaderboard", color=discord.Color.gold())

        text = ""

        for i, (user, amount) in enumerate(sorted_users, 1):

            member = ctx.guild.get_member(int(user))

            name = member.name if member else "Unknown"

            text += f"{i}. {name} — {amount}\n"

        embed.description = text

        await ctx.send(embed=embed)

    @commands.hybrid_command(description="Countreset command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def countreset(self, ctx):

        save(default_data())

        await ctx.send("✅ Counter has been reset")


async def setup(bot):

    await bot.add_cog(Count(bot))
