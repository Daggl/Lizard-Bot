"""Birthday tracking cog — stores birthdays and posts daily announcements."""

import datetime
import re

import discord
from discord.ext import commands, tasks

from mybot.utils.config import load_cog_config
from mybot.utils.i18n import resolve_localized_value, translate
from mybot.utils.jsonstore import safe_load_json, safe_save_json
from mybot.utils.paths import guild_data_path

_BIRTHDAY_RE = re.compile(r"^\d{1,2}\.\d{1,2}$")


def load_birthdays(guild_id: int | str | None = None) -> dict:
    path = guild_data_path(guild_id, "birthdays_data.json")
    if not path:
        return {}
    return safe_load_json(path, default={})


def save_birthdays(guild_id: int | str | None, data: dict):
    path = guild_data_path(guild_id, "birthdays_data.json")
    if path:
        safe_save_json(path, data)


def load_sent_birthdays(guild_id: int | str | None = None) -> dict:
    path = guild_data_path(guild_id, "birthdays_sent.json")
    if not path:
        return {}
    return safe_load_json(path, default={})


def save_sent_birthdays(guild_id: int | str | None, data: dict):
    path = guild_data_path(guild_id, "birthdays_sent.json")
    if path:
        safe_save_json(path, data)


def _cfg(guild_id: int | str | None = None) -> dict:
    try:
        return load_cog_config("birthdays", guild_id=guild_id) or {}
    except Exception:
        return {}


def _channel_id(guild_id: int | str | None = None) -> int:
    try:
        return int(_cfg(guild_id).get("CHANNEL_ID", 0) or 0)
    except Exception:
        return 0


def _embed_title(guild_id: int | None = None) -> str:
    try:
        raw = _cfg(guild_id).get("EMBED_TITLE", "")
        return str(resolve_localized_value(raw, guild_id=guild_id) or "")
    except Exception:
        return ""


def _embed_description(guild_id: int | None = None) -> str:
    try:
        raw = _cfg(guild_id).get("EMBED_DESCRIPTION", "")
        return str(resolve_localized_value(raw, guild_id=guild_id) or "")
    except Exception:
        return ""


def _embed_footer(guild_id: int | None = None) -> str:
    try:
        raw = _cfg(guild_id).get("EMBED_FOOTER", "")
        return str(resolve_localized_value(raw, guild_id=guild_id) or "")
    except Exception:
        return ""


def _embed_color(guild_id: int | str | None = None) -> discord.Color:
    raw = ""
    try:
        raw = str(_cfg(guild_id).get("EMBED_COLOR", "") or "").strip()
    except Exception:
        pass
    try:
        if not raw:
            return discord.Color.default()
        if raw.startswith("#"):
            raw = raw[1:]
        return discord.Color(int(raw, 16))
    except Exception:
        return discord.Color.default()


def _safe_format(template: str, values: dict) -> str:
    class _Default(dict):
        def __missing__(self, key):
            return "{" + str(key) + "}"

    try:
        return str(template).format_map(_Default(values or {}))
    except Exception:
        return str(template)


class Birthdays(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    @commands.hybrid_command(name="birthday", description="Set your birthday (DD.MM).")
    async def birthday(self, ctx: commands.Context, date: str):
        """Save the user's birthday after validating the DD.MM format."""
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)

        # Validate format: DD.MM
        if not _BIRTHDAY_RE.match(date):
            await ctx.send(translate(
                "birthdays.error.invalid_format",
                guild_id=guild_id,
                default="❌ Invalid date format. Please use DD.MM (e.g. 25.12).",
            ))
            return

        # Validate the actual date values
        try:
            day, month = date.split(".")
            datetime.date(2000, int(month), int(day))  # leap year to allow 29.02
        except (ValueError, IndexError):
            await ctx.send(translate(
                "birthdays.error.invalid_date",
                guild_id=guild_id,
                default="❌ Invalid date. Day or month out of range.",
            ))
            return

        if guild_id is None:
            await ctx.send("❌ This command must be used in a server.")
            return

        birthdays = load_birthdays(guild_id)
        # Normalise to zero-padded DD.MM format for reliable matching
        day, month = date.split(".")
        normalised = f"{int(day):02d}.{int(month):02d}"
        birthdays[str(ctx.author.id)] = normalised
        save_birthdays(guild_id, birthdays)

        await ctx.send(translate("birthdays.msg.saved", guild_id=guild_id, date=normalised))

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        """Check birthdays for all guilds the bot is in."""
        now = datetime.datetime.now()
        today = now.strftime("%d.%m")
        today_key = now.strftime("%Y-%m-%d")

        for guild in self.bot.guilds:
            guild_id = guild.id
            channel_id = _channel_id(guild_id)
            if not channel_id:
                continue  # No birthday channel configured for this guild

            channel = self.bot.get_channel(int(channel_id))
            if channel is None:
                channel = guild.get_channel(int(channel_id))
            if channel is None:
                continue

            birthdays = load_birthdays(guild_id)
            sent = load_sent_birthdays(guild_id)

            # cleanup old sent markers to keep file small (keep only today)
            if isinstance(sent, dict):
                sent = {k: v for k, v in sent.items() if k == today_key}
            else:
                sent = {}

            sent_today = sent.get(today_key, [])
            if not isinstance(sent_today, list):
                sent_today = []
            sent_today_set = {str(uid) for uid in sent_today}

            for user_id, date in birthdays.items():
                if date != today:
                    continue
                if str(user_id) in sent_today_set:
                    continue

                try:
                    user = await self.bot.fetch_user(int(user_id))
                    values = {
                        "mention": user.mention,
                        "user_name": getattr(user, "name", "User"),
                        "display_name": getattr(user, "display_name", getattr(user, "name", "User")),
                        "user_id": getattr(user, "id", 0),
                        "date": today,
                    }
                    embed = discord.Embed(
                        title=_safe_format(_embed_title(guild_id), values),
                        description=_safe_format(_embed_description(guild_id), values),
                        color=_embed_color(guild_id),
                    )
                    footer = _safe_format(_embed_footer(guild_id), values).strip()
                    if footer:
                        embed.set_footer(text=footer)
                    await channel.send(embed=embed)
                    sent_today_set.add(str(user_id))
                except Exception as exc:
                    print(f"[Birthdays] Error checking birthday for user {user_id} in guild {guild_id}: {exc}")

            sent[today_key] = sorted(list(sent_today_set))
            save_sent_birthdays(guild_id, sent)

    @check_birthdays.before_loop
    async def before_check(self):

        await self.bot.wait_until_ready()


async def setup(bot):

    await bot.add_cog(Birthdays(bot))
