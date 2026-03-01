"""Leveling cog — XP gain on messages, level-up announcements and role rewards."""

import logging

import discord
from discord.ext import commands

from .utils.database import Database
from .utils.level_config import (get_achievement_channel_id, get_level_base_xp,
                                 get_level_xp_step, get_levelup_channel_id,
                                 get_message_templates)

log = logging.getLogger(__name__)

# ======================================================
# XP FORMULA
# ======================================================


def xp_for_level(level: int, guild_id: int | str | None = None) -> int:
    """
    XP required to advance FROM this level to next level.

    MEE6 style formula:
    smooth progression, no level 0 bug
    
    IMPORTANT: Must pass guild_id for per-guild config!
    Default fallbacks (100 base, 50 step) prevent infinite loop if config missing.
    """

    base = get_level_base_xp(guild_id=guild_id)
    step = get_level_xp_step(guild_id=guild_id)
    return max(1, base + (level * step))  # Never return 0 to prevent infinite loop!


# ======================================================
# LEVELS COG
# ======================================================


class Levels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

        # global access
        bot.db = self.db

    async def _resolve_levelup_channel(self, member: discord.Member):
        # If a UI test override is active, always use that channel
        override = getattr(self.bot, "_ui_test_channel_override", None)
        if override is not None:
            return override

        guild = getattr(member, "guild", None)
        channel_id = get_levelup_channel_id(guild_id=getattr(guild, 'id', None))

        channel = None
        if channel_id > 0:
            channel = self.bot.get_channel(channel_id)
            if channel is None and guild is not None:
                channel = guild.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception:
                    channel = None

        if channel is not None and guild is not None and getattr(channel, "guild", None) != guild:
            channel = None

        if channel is None and guild is not None:
            if guild.system_channel is not None:
                channel = guild.system_channel
            else:
                me = getattr(guild, "me", None)
                for text_channel in getattr(guild, "text_channels", []):
                    try:
                        perms = text_channel.permissions_for(me) if me else None
                        if perms and perms.send_messages:
                            channel = text_channel
                            break
                    except Exception:
                        continue

        return channel

    # ==================================================

    async def add_xp(self, member, amount: int):
        guild_id = getattr(getattr(member, "guild", None), "id", None)

        user = self.db.get_user(member.id, guild_id=guild_id)

        user["xp"] += int(amount)

        leveled = False

        # ==================================================
        # LEVEL LOOP - calculate all level-ups first (no messages inside loop!)
        # ==================================================

        while user["xp"] >= xp_for_level(user["level"], guild_id=guild_id):

            needed = xp_for_level(user["level"], guild_id=guild_id)

            user["xp"] -= needed

            user["level"] += 1

            leveled = True

        # ==================================================
        # LEVEL UP MESSAGE - send ONE message after all level-ups calculated
        # ==================================================

        if leveled:
            channel = await self._resolve_levelup_channel(member)

            if channel:
                try:
                    level_up_tpl, _achievement_tpl = get_message_templates(guild_id)
                    template_raw = str(level_up_tpl)
                    description = template_raw.format(
                        member_mention=member.mention,
                        member_name=getattr(member, "name", member.display_name),
                        member_display_name=member.display_name,
                        member_id=member.id,
                        guild_name=getattr(getattr(member, "guild", None), "name", ""),
                        level=user["level"],
                    )
                except Exception:
                    description = (
                        f"{member.mention}\n"
                        f"you just reached level {user['level']}!\n"
                        f"keep it up, cutie!"
                    )

                embed = discord.Embed(
                    description=description,
                    color=0x5865F2,
                )

                embed.set_thumbnail(url=member.display_avatar.url)
                try:
                    await channel.send(embed=embed)
                except Exception as send_exc:
                    log.warning("Failed to send level-up message in channel %s: %s", getattr(channel, 'id', 'unknown'), send_exc)

        # ==================================================
        # REWARDS
        # ==================================================

        if leveled:

            rewards_cog = self.bot.get_cog("Rewards")

            if rewards_cog:

                await rewards_cog.check_rewards(member)

        # ==================================================
        # SAVE
        # ==================================================

        self.db.save(guild_id=guild_id)


# ======================================================
# SETUP
# ======================================================


async def setup(bot):

    await bot.add_cog(Levels(bot))
