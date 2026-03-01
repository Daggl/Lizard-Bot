"""Birthday tracking cog — stores birthdays and posts daily announcements.

Features:
- /birthday DD.MM — save your birthday
- /birthdaypanel — post an interactive birthday overview panel (admin)
- Daily check: assign a birthday role on the day and remove it the next day.
"""

import datetime
import re

import discord
from discord import app_commands
from discord.ext import commands, tasks

from mybot.utils.config import load_cog_config
from mybot.utils.i18n import resolve_localized_value, translate
from mybot.utils.jsonstore import safe_load_json, safe_save_json
from mybot.utils.paths import guild_data_path

_BIRTHDAY_RE = re.compile(r"^\d{1,2}\.\d{1,2}$")

# Month names for display
_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


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


def _role_id(guild_id: int | str | None = None) -> int:
    """Return the birthday role ID for the guild (0 = disabled)."""
    try:
        return int(_cfg(guild_id).get("ROLE_ID", 0) or 0)
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


# ---------------------------------------------------------------------------
# Birthday Panel View
# ---------------------------------------------------------------------------

class BirthdayPanelView(discord.ui.View):
    """Persistent view with buttons to browse saved birthdays."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 All Birthdays", style=discord.ButtonStyle.primary, custom_id="birthday_panel:all")
    async def show_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild_id
        birthdays = load_birthdays(guild_id)
        if not birthdays:
            await interaction.response.send_message(
                translate("birthdays.panel.no_birthdays", guild_id=guild_id,
                          default="📭 No birthdays saved yet."),
                ephemeral=True,
            )
            return

        # Group by month
        by_month: dict[int, list[tuple[str, int, int]]] = {}
        for user_id, date_str in birthdays.items():
            try:
                day, month = date_str.split(".")
                by_month.setdefault(int(month), []).append((user_id, int(day), int(month)))
            except Exception:
                continue

        lines = []
        for month_num in sorted(by_month.keys()):
            month_name = _MONTH_NAMES.get(month_num, str(month_num))
            entries = sorted(by_month[month_num], key=lambda e: e[1])
            lines.append(f"**{month_name}**")
            for uid, day, _m in entries:
                lines.append(f"  {day:02d}.{_m:02d} — <@{uid}>")
            lines.append("")

        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3900] + "\n…"

        embed = discord.Embed(
            title=translate("birthdays.panel.all_title", guild_id=guild_id,
                            default="🎂 All Birthdays"),
            description=text,
            color=_embed_color(guild_id),
        )
        embed.set_footer(text=f"{len(birthdays)} birthdays saved")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔜 Upcoming", style=discord.ButtonStyle.secondary, custom_id="birthday_panel:upcoming")
    async def show_upcoming(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild_id
        birthdays = load_birthdays(guild_id)
        if not birthdays:
            await interaction.response.send_message(
                translate("birthdays.panel.no_birthdays", guild_id=guild_id,
                          default="📭 No birthdays saved yet."),
                ephemeral=True,
            )
            return

        now = datetime.datetime.now()
        today_tuple = (now.month, now.day)

        entries = []
        for user_id, date_str in birthdays.items():
            try:
                day, month = date_str.split(".")
                d, m = int(day), int(month)
                # Days until birthday (wrapping around year)
                try:
                    bday_this_year = datetime.date(now.year, m, d)
                except ValueError:
                    bday_this_year = datetime.date(now.year, m, min(d, 28))
                delta = (bday_this_year - now.date()).days
                if delta < 0:
                    delta += 365
                entries.append((delta, d, m, user_id))
            except Exception:
                continue

        entries.sort()
        upcoming = entries[:15]

        lines = []
        for delta, day, month, uid in upcoming:
            month_name = _MONTH_NAMES.get(month, str(month))
            if delta == 0:
                label = "🎉 **TODAY!**"
            elif delta == 1:
                label = "Tomorrow"
            else:
                label = f"in {delta} days"
            lines.append(f"{day:02d}. {month_name} — <@{uid}> ({label})")

        embed = discord.Embed(
            title=translate("birthdays.panel.upcoming_title", guild_id=guild_id,
                            default="🔜 Upcoming Birthdays"),
            description="\n".join(lines),
            color=_embed_color(guild_id),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class Birthdays(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # Register persistent view so buttons work after restart
        self.bot.add_view(BirthdayPanelView())
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    # ------------------------------------------------------------------
    # /birthday DD.MM
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # /birthdaypanel — post a persistent birthday overview panel
    # ------------------------------------------------------------------

    @commands.hybrid_command(name="birthdaypanel", description="Post the birthday overview panel.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def birthdaypanel(self, ctx: commands.Context):
        """Post an embed with buttons to view all birthdays and upcoming ones."""
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)

        embed = discord.Embed(
            title=translate("birthdays.panel.title", guild_id=guild_id,
                            default="🎂 Birthday Panel"),
            description=translate("birthdays.panel.description", guild_id=guild_id,
                                  default="Click the buttons below to view all saved birthdays or see who has a birthday coming up!"),
            color=_embed_color(guild_id),
        )
        await ctx.send(embed=embed, view=BirthdayPanelView())

    # ------------------------------------------------------------------
    # Daily birthday check (announcement + role)
    # ------------------------------------------------------------------

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        """Check birthdays for all guilds the bot is in."""
        now = datetime.datetime.now()
        today = now.strftime("%d.%m")
        today_key = now.strftime("%Y-%m-%d")

        for guild in self.bot.guilds:
            guild_id = guild.id
            channel_id = _channel_id(guild_id)
            role_id = _role_id(guild_id)

            channel = None
            if channel_id:
                channel = self.bot.get_channel(int(channel_id))
                if channel is None:
                    channel = guild.get_channel(int(channel_id))

            # Resolve birthday role object
            birthday_role = None
            if role_id:
                birthday_role = guild.get_role(int(role_id))

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

            # --- Remove birthday role from users whose birthday is NOT today ---
            if birthday_role:
                for member in birthday_role.members:
                    user_bd = birthdays.get(str(member.id))
                    if user_bd != today:
                        try:
                            await member.remove_roles(birthday_role, reason="Birthday is over")
                        except Exception as exc:
                            print(f"[Birthdays] Failed to remove birthday role from {member.id}: {exc}")

            # --- Process today's birthdays ---
            for user_id, date in birthdays.items():
                if date != today:
                    continue

                # Assign birthday role (even if already announced)
                if birthday_role:
                    try:
                        member = guild.get_member(int(user_id))
                        if member and birthday_role not in member.roles:
                            await member.add_roles(birthday_role, reason="Happy Birthday!")
                    except Exception as exc:
                        print(f"[Birthdays] Failed to assign birthday role to {user_id}: {exc}")

                # Send announcement (only once per day)
                if str(user_id) in sent_today_set:
                    continue
                if channel is None:
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
