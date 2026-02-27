"""Birthday tracking cog — stores birthdays and posts daily announcements."""

import datetime
import os
import re

import discord
from discord.ext import commands, tasks

from mybot.utils.config import load_cog_config
from mybot.utils.i18n import resolve_localized_value, translate
from mybot.utils.jsonstore import safe_load_json, safe_save_json

_BIRTHDAY_RE = re.compile(r"^\d{1,2}\.\d{1,2}$")

DATA_FOLDER = "data"
BIRTHDAY_FILE = os.path.join(DATA_FOLDER, "birthdays.json")
SENT_FILE = os.path.join(DATA_FOLDER, "birthdays_sent.json")


def load_birthdays():
    return safe_load_json(BIRTHDAY_FILE, default={})


def save_birthdays(data):
    safe_save_json(BIRTHDAY_FILE, data)


def load_sent_birthdays():
    return safe_load_json(SENT_FILE, default={})


def save_sent_birthdays(data):
    safe_save_json(SENT_FILE, data)


def _cfg() -> dict:
    try:
        return load_cog_config("birthdays") or {}
    except Exception:
        return {}


def _channel_id() -> int:
    try:
        return int(_cfg().get("CHANNEL_ID", 0) or 0)
    except Exception:
        return 0


def _embed_title(guild_id: int | None = None) -> str:
    try:
        raw = _cfg().get("EMBED_TITLE", "")
        return str(resolve_localized_value(raw, guild_id=guild_id) or "")
    except Exception:
        return ""


def _embed_description(guild_id: int | None = None) -> str:
    try:
        raw = _cfg().get("EMBED_DESCRIPTION", "")
        return str(resolve_localized_value(raw, guild_id=guild_id) or "")
    except Exception:
        return ""


def _embed_footer(guild_id: int | None = None) -> str:
    try:
        raw = _cfg().get("EMBED_FOOTER", "")
        return str(resolve_localized_value(raw, guild_id=guild_id) or "")
    except Exception:
        return ""


def _embed_color() -> discord.Color:
    raw = ""
    try:
        raw = str(_cfg().get("EMBED_COLOR", "") or "").strip()
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

        birthdays = load_birthdays()
        birthdays[str(ctx.author.id)] = date
        save_birthdays(birthdays)

        await ctx.send(translate("birthdays.msg.saved", guild_id=guild_id, date=date))

    @tasks.loop(hours=24)
    async def check_birthdays(self):

        birthdays = load_birthdays()
        sent = load_sent_birthdays()
        channel_id = _channel_id()

        now = datetime.datetime.now()
        today = now.strftime("%d.%m")
        today_key = now.strftime("%Y-%m-%d")

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

            if date == today:
                if str(user_id) in sent_today_set:
                    continue

                try:

                    user = await self.bot.fetch_user(int(user_id))

                    channel = None
                    if channel_id:
                        channel = self.bot.get_channel(int(channel_id))

                    if channel is not None:
                        guild_id = getattr(getattr(channel, "guild", None), "id", None)
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
                            color=_embed_color(),
                        )
                        footer = _safe_format(_embed_footer(guild_id), values).strip()
                        if footer:
                            embed.set_footer(text=footer)
                        await channel.send(embed=embed)
                        sent_today_set.add(str(user_id))

                except Exception as exc:
                    print(f"[Birthdays] Error checking birthday for user {user_id}: {exc}")

        sent[today_key] = sorted(list(sent_today_set))
        save_sent_birthdays(sent)

    @check_birthdays.before_loop
    async def before_check(self):

        await self.bot.wait_until_ready()


async def setup(bot):

    await bot.add_cog(Birthdays(bot))
