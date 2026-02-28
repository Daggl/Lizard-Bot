"""Counting game cog — tracks sequential counting in a dedicated channel."""

import discord
from discord import app_commands
from discord.ext import commands

from mybot.utils.config import load_cog_config
from mybot.utils.i18n import translate
from mybot.utils.jsonstore import safe_load_json, safe_save_json
from mybot.utils.paths import guild_data_path


def _cfg(guild_id: int | str | None = None) -> dict:
    try:
        return load_cog_config("count", guild_id=guild_id) or {}
    except Exception:
        return {}


def _count_channel_id(guild_id: int | str | None = None):
    try:
        raw = _cfg(guild_id).get("COUNT_CHANNEL_ID", None)
        return int(raw) if raw is not None else None
    except Exception:
        return None


def _min_count_for_record(guild_id: int | str | None = None) -> int:
    try:
        return int(_cfg(guild_id).get("MIN_COUNT_FOR_RECORD", 150) or 150)
    except Exception:
        return 150


def default_data():
    return {
        "current": 0,
        "last_user": None,
        "record": 0,
        "record_holder": None,
        "total_counts": {},
        "fails": 0,
    }


def load(guild_id: int | str | None = None) -> dict:
    path = guild_data_path(guild_id, "count_data.json")
    if not path:
        return default_data()
    return safe_load_json(path, default=default_data())


def save(guild_id: int | str | None, data: dict):
    path = guild_data_path(guild_id, "count_data.json")
    if path:
        safe_save_json(path, data)


class Count(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        guild_id = getattr(getattr(message, "guild", None), "id", None)
        if guild_id is None:
            return

        count_channel_id = _count_channel_id(guild_id)
        if count_channel_id and message.channel.id != count_channel_id:
            return

        data = load(guild_id)

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
                translate(
                    "count.msg.error",
                    guild_id=guild_id,
                    expected=expected,
                    record=data["record"],
                )
            )

            data["current"] = 0

            data["last_user"] = None

            data["fails"] += 1

            save(guild_id, data)

            return

        await message.add_reaction("✅")

        data["current"] = number

        data["last_user"] = str(message.author.id)

        user = str(message.author.id)

        if user not in data["total_counts"]:
            data["total_counts"][user] = 0

        data["total_counts"][user] += 1

        min_count_for_record = _min_count_for_record(guild_id)
        if number > data["record"] and number >= min_count_for_record:

            data["record"] = number

            data["record_holder"] = str(message.author.id)

            await message.channel.send(
                translate(
                    "count.msg.new_record",
                    guild_id=guild_id,
                    number=number,
                    user=message.author.mention,
                )
            )

        save(guild_id, data)

    @commands.hybrid_command(description="Countstats command.")
    async def countstats(self, ctx):

        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        data = load(guild_id)

        embed = discord.Embed(title=translate("count.embed.stats.title", guild_id=guild_id), color=discord.Color.blue())

        embed.add_field(name=translate("count.embed.stats.current", guild_id=guild_id), value=data["current"])

        embed.add_field(name=translate("count.embed.stats.record", guild_id=guild_id), value=data["record"])

        embed.add_field(name=translate("count.embed.stats.fails", guild_id=guild_id), value=data["fails"])

        await ctx.send(embed=embed)

    @commands.hybrid_command(description="Counttop command.")
    async def counttop(self, ctx):

        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        data = load(guild_id)

        sorted_users = sorted(
            data["total_counts"].items(), key=lambda x: x[1], reverse=True
        )[:10]

        embed = discord.Embed(title=translate("count.embed.top.title", guild_id=guild_id), color=discord.Color.gold())

        text = ""

        for i, (user, amount) in enumerate(sorted_users, 1):

            member = ctx.guild.get_member(int(user))

            name = member.name if member else translate("count.label.unknown_user", guild_id=guild_id)

            text += f"{i}. {name} — {amount}\n"

        embed.description = text

        await ctx.send(embed=embed)

    @commands.hybrid_command(description="Countreset command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def countreset(self, ctx):

        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        save(guild_id, default_data())

        await ctx.send(translate("count.msg.reset", guild_id=guild_id))


async def setup(bot):

    await bot.add_cog(Count(bot))
