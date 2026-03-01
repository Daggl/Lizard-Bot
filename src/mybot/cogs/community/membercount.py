"""Member-count channel cog — keeps a voice channel name in sync with the
current server member count.

The channel is a **voice channel** that no one actually joins; its name is
updated periodically to show the live member count, e.g. ``👥 Members: 123``.

Per-guild configuration is stored in ``config/guilds/{guild_id}/membercount.json``
with the keys:
  - ``CHANNEL_ID``  — the voice channel to rename
  - ``TEMPLATE``    — name template, default ``👥 Members: {count}``
"""

import asyncio
import logging

import discord
from discord.ext import commands, tasks

from mybot.utils.config import load_cog_config
from mybot.utils.feature_flags import is_feature_enabled

log = logging.getLogger(__name__)

_DEFAULT_TEMPLATE = "{count} 👥 Members"
_UPDATE_INTERVAL_MINUTES = 10  # Discord rate-limits channel renames


def _cfg(guild_id) -> dict:
    try:
        return load_cog_config("membercount", guild_id=guild_id) or {}
    except Exception:
        return {}


class MemberCount(commands.Cog):
    """Keeps a voice channel name reflecting the server's member count."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._update_loop.start()

    def cog_unload(self):
        self._update_loop.cancel()

    # ------------------------------------------------------------------
    # Core update logic
    # ------------------------------------------------------------------

    async def _update_guild(self, guild: discord.Guild):
        guild_id = guild.id
        if not is_feature_enabled(guild_id, "membercount"):
            return
        cfg = _cfg(guild_id)
        channel_id = int(cfg.get("CHANNEL_ID", 0) or 0)
        if channel_id <= 0:
            return

        template = str(cfg.get("TEMPLATE", "") or "") or _DEFAULT_TEMPLATE
        count = guild.member_count or len(guild.members)
        new_name = template.format(count=count)

        channel = guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                return

        if channel is None:
            return

        # Only rename if name actually changed to avoid unnecessary API calls
        if getattr(channel, "name", None) == new_name:
            return

        try:
            await channel.edit(name=new_name)
        except discord.HTTPException as exc:
            log.warning("MemberCount: failed to rename channel %s: %s", channel_id, exc)
        except Exception as exc:
            log.warning("MemberCount: unexpected error renaming channel %s: %s", channel_id, exc)

    # ------------------------------------------------------------------
    # Periodic task
    # ------------------------------------------------------------------

    @tasks.loop(minutes=_UPDATE_INTERVAL_MINUTES)
    async def _update_loop(self):
        for guild in self.bot.guilds:
            try:
                await self._update_guild(guild)
            except Exception as exc:
                log.warning("MemberCount loop error for guild %s: %s", guild.id, exc)
            # Small delay between guilds to avoid rate limits
            await asyncio.sleep(2)

    @_update_loop.before_loop
    async def _before_update_loop(self):
        await self.bot.wait_until_ready()

    # ------------------------------------------------------------------
    # Event listeners — update on join/leave for immediate feedback
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            await self._update_guild(member.guild)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            await self._update_guild(member.guild)
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberCount(bot))
