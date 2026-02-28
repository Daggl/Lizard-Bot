"""Cog to bulk-delete messages from a specific user within a time range.

Provides both a hybrid slash/prefix command and a control-API action
so the local UI can trigger purges remotely.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

try:
    from mybot.utils.i18n import translate_for_ctx
except ImportError:
    from src.mybot.utils.i18n import translate_for_ctx


class Purge(commands.Cog):
    """Bulk-delete messages from a specific user within a time window."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # background purge state (for UI progress polling)
        self._purge_running = False
        self._purge_deleted = 0
        self._purge_current_channel = ""
        self._purge_started_at: float = 0.0
        self._purge_finished = False
        self._purge_error: str | None = None

    # ------------------------------------------------------------------
    # helper: the actual purge logic, reusable from command + API
    # ------------------------------------------------------------------

    async def purge_user_messages(
        self,
        channel: discord.TextChannel,
        user_id: int,
        after: datetime,
        before: datetime,
        *,
        reason: str | None = None,
        progress_callback=None,
    ) -> int:
        """Delete all messages by *user_id* in *channel* between *after* and *before*.

        Returns the number of deleted messages.
        Discord only allows bulk-delete for messages < 14 days old, so older
        messages are deleted one-by-one (slower, but works).

        *progress_callback(deleted, channel_name)* is called periodically.
        """
        deleted = 0
        now = datetime.now(timezone.utc)
        bulk_cutoff = now - timedelta(days=14)

        bot_id = getattr(getattr(self.bot, "user", None), "id", None)
        is_self = (user_id == bot_id)

        # Collect messages in batches
        bulk_queue: list[discord.Message] = []
        single_queue: list[discord.Message] = []

        async for msg in channel.history(after=after, before=before, limit=None, oldest_first=True):
            if msg.author.id != user_id:
                continue
            if msg.created_at >= bulk_cutoff:
                bulk_queue.append(msg)
            else:
                single_queue.append(msg)

        total = len(bulk_queue) + len(single_queue)
        if total > 0:
            print(f"[Purge] #{channel.name}: found {total} messages "
                  f"({len(bulk_queue)} bulk, {len(single_queue)} single)")

        # Bulk-delete (up to 100 at a time, messages < 14 days)
        for i in range(0, len(bulk_queue), 100):
            batch = bulk_queue[i : i + 100]
            try:
                await channel.delete_messages(batch, reason=reason)
                deleted += len(batch)
            except discord.HTTPException:
                # Fallback: delete one by one
                for m in batch:
                    try:
                        await m.delete()
                        deleted += 1
                    except discord.NotFound:
                        pass  # already gone, don't count
                    except discord.HTTPException:
                        pass
                    await asyncio.sleep(0.35)
            if progress_callback:
                progress_callback(deleted, channel.name)

        # Single-delete for old messages (> 14 days)
        for idx, m in enumerate(single_queue):
            try:
                await m.delete()
                deleted += 1
            except discord.NotFound:
                pass  # already gone, don't count
            except discord.HTTPException:
                pass
            # Rate limit: bot's own messages are a bit more lenient
            await asyncio.sleep(0.25 if is_self else 0.35)
            # Progress update every 50 messages
            if progress_callback and (idx + 1) % 50 == 0:
                progress_callback(deleted, channel.name)

        if total > 0:
            print(f"[Purge] #{channel.name}: deleted {deleted}/{total}")

        return deleted

    # ------------------------------------------------------------------
    # background purge (for UI / control API)
    # ------------------------------------------------------------------

    async def run_background_purge(
        self,
        channels: list[discord.TextChannel],
        user_id: int,
        after: datetime,
        before: datetime,
        reason: str = "Purge via UI",
    ):
        """Run a purge across multiple channels as a background task.

        Updates ``self._purge_*`` attributes for progress polling.
        """
        self._purge_running = True
        self._purge_deleted = 0
        self._purge_current_channel = ""
        self._purge_started_at = time.time()
        self._purge_finished = False
        self._purge_error = None

        def _progress(deleted_in_ch: int, ch_name: str):
            self._purge_current_channel = ch_name

        try:
            me = channels[0].guild.me if channels else None
            for ch in channels:
                if me is not None:
                    try:
                        perms = ch.permissions_for(me)
                        if not (perms.read_message_history and perms.manage_messages):
                            continue
                    except Exception:
                        continue

                self._purge_current_channel = ch.name
                count = await self.purge_user_messages(
                    ch, user_id, after=after, before=before,
                    reason=reason, progress_callback=_progress,
                )
                self._purge_deleted += count

            elapsed = time.time() - self._purge_started_at
            print(f"[Purge] DONE — {self._purge_deleted} messages deleted in {elapsed:.1f}s")
        except Exception as e:
            self._purge_error = str(e)
            print(f"[Purge] ERROR: {e}")
        finally:
            self._purge_running = False
            self._purge_finished = True

    def get_purge_status(self) -> dict:
        """Return current purge status for UI polling."""
        elapsed = 0.0
        if self._purge_started_at:
            elapsed = time.time() - self._purge_started_at
        return {
            "running": self._purge_running,
            "deleted": self._purge_deleted,
            "channel": self._purge_current_channel,
            "elapsed_seconds": round(elapsed, 1),
            "finished": self._purge_finished,
            "error": self._purge_error,
        }

    # ------------------------------------------------------------------
    # slash / prefix command
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="purge",
        description="Delete all messages from a user in a time range.",
    )
    @app_commands.describe(
        user="The user whose messages should be deleted.",
        hours="Delete messages from the last N hours (default: 24).",
        channel="Channel to purge in (default: current channel).",
    )
    @app_commands.default_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge_cmd(
        self,
        ctx: commands.Context,
        user: discord.User,
        hours: Optional[int] = 24,
        channel: Optional[discord.TextChannel] = None,
    ):
        target_channel = channel or ctx.channel
        if not isinstance(target_channel, discord.TextChannel):
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "purge.error.text_channel_only",
                    default="❌ Purge only works in text channels.",
                ),
                ephemeral=True,
            )
            return

        hours = max(1, min(hours or 24, 8760))  # clamp 1h – 365d
        now = datetime.now(timezone.utc)
        after = now - timedelta(hours=hours)

        # Defer because this can take a while
        await ctx.defer(ephemeral=True)

        reason = f"Purge by {ctx.author} ({ctx.author.id})"
        deleted = await self.purge_user_messages(
            target_channel,
            user.id,
            after=after,
            before=now,
            reason=reason,
        )

        await ctx.send(
            translate_for_ctx(
                ctx,
                "purge.msg.done",
                default="🗑 Deleted **{count}** message(s) from {user} in {channel} (last {hours}h).",
                count=deleted,
                user=user.mention,
                channel=target_channel.mention,
                hours=hours,
            ),
            ephemeral=True,
        )

    # ------------------------------------------------------------------
    # multi-channel variant (all text channels in the guild)
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="purgeall",
        description="Delete all messages from a user across ALL text channels.",
    )
    @app_commands.describe(
        user="The user whose messages should be deleted.",
        hours="Delete messages from the last N hours (default: 24).",
    )
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def purgeall_cmd(
        self,
        ctx: commands.Context,
        user: discord.User,
        hours: Optional[int] = 24,
    ):
        if ctx.guild is None:
            await ctx.send("❌ This command can only be used in a server.", ephemeral=True)
            return

        hours = max(1, min(hours or 24, 8760))
        now = datetime.now(timezone.utc)
        after = now - timedelta(hours=hours)

        await ctx.defer(ephemeral=True)

        reason = f"Purge-all by {ctx.author} ({ctx.author.id})"
        total = 0
        me = ctx.guild.me

        for ch in ctx.guild.text_channels:
            perms = ch.permissions_for(me)
            if not (perms.read_message_history and perms.manage_messages):
                continue
            count = await self.purge_user_messages(
                ch, user.id, after=after, before=now, reason=reason,
            )
            total += count

        await ctx.send(
            translate_for_ctx(
                ctx,
                "purge.msg.done_all",
                default="🗑 Deleted **{count}** message(s) from {user} across all channels (last {hours}h).",
                count=total,
                user=user.mention,
                hours=hours,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Purge(bot))
