"""Admin tools cog — leveling manipulation, test commands and diagnostic utilities."""

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

try:
    from mybot.utils.i18n import translate_for_ctx
except Exception:  # pragma: no cover - fallback for relative imports during packaging
    from src.mybot.utils.i18n import translate_for_ctx


class AdminTools(commands.Cog):
    """Administrative commands for leveling, achievements and bot testing."""

    def __init__(self, bot):
        self.bot = bot

    def _cmd(self, name: str):
        return self.bot.get_command(name)

    async def _invoke_or_error(self, ctx, command_name: str, **kwargs):
        cmd = self._cmd(command_name)
        if cmd is None:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.error.command_unavailable",
                    default="❌ Command not available: `{command}`",
                    command=command_name,
                )
            )
            return False
        await ctx.invoke(cmd, **kwargs)
        return True

    def _get_user_data(self, member: discord.Member, guild_id=None):
        gid = guild_id or getattr(getattr(member, 'guild', None), 'id', None)
        return self.bot.db.get_user(member.id, guild_id=gid)

    def _xp_for_level(self, level: int, guild_id=None) -> int:
        """Calculate the XP needed for a given level."""
        try:
            from mybot.cogs.leveling.utils.level_config import (
                get_level_base_xp,
                get_level_xp_step,
            )
        except ImportError:
            from src.mybot.cogs.leveling.utils.level_config import (
                get_level_base_xp,
                get_level_xp_step,
            )

        base = get_level_base_xp(guild_id=guild_id)
        step = get_level_xp_step(guild_id=guild_id)
        return max(1, base + (int(level) * step))

    # XP GEBEN
    @commands.hybrid_command(description="Givexp command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def givexp(self, ctx, member: discord.Member, amount: int):
        guild_id = getattr(ctx.guild, 'id', None)
        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        user["xp"] += amount
        self.bot.db.save(guild_id=guild_id)

        await ctx.send(
            translate_for_ctx(
                ctx,
                "admin.msg.xp_given",
                default="✅ {member} got {amount} XP.",
                member=member.mention,
                amount=amount,
            )
        )

    # XP SETZEN
    @commands.hybrid_command(description="Setxp command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def setxp(self, ctx, member: discord.Member, amount: int):
        guild_id = getattr(ctx.guild, 'id', None)
        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        user["xp"] = amount
        self.bot.db.save(guild_id=guild_id)

        await ctx.send(
            translate_for_ctx(
                ctx,
                "admin.msg.xp_set",
                default="🛠 XP of {member} set to {amount}.",
                member=member.mention,
                amount=amount,
            )
        )

    # LEVEL SETZEN
    @commands.hybrid_command(description="Setlevel command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def setlevel(self, ctx, member: discord.Member, level: int):
        guild_id = getattr(ctx.guild, 'id', None)
        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        user["level"] = level
        self.bot.db.save(guild_id=guild_id)

        await ctx.send(
            translate_for_ctx(
                ctx,
                "admin.msg.level_set",
                default="⭐ Level of {member} set to {level}.",
                member=member.mention,
                level=level,
            )
        )

    @commands.hybrid_command(description="Giveachievement command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def giveachievement(self, ctx, member: discord.Member, *, name: str):
        guild_id = getattr(ctx.guild, 'id', None)
        user = self._get_user_data(member, guild_id=guild_id)

        if name in user["achievements"]:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.error.achievement_exists",
                    default="❌ Achievement already exists.",
                )
            )
            return

        user["achievements"].append(name)
        self.bot.db.save(guild_id=guild_id)

        await ctx.send(
            translate_for_ctx(
                ctx,
                "admin.msg.achievement_given",
                default="🏆 Achievement '{name}' was given to {member}.",
                name=name,
                member=member.mention,
            )
        )

    @commands.hybrid_command(description="Removeachievement command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def removeachievement(self, ctx, member: discord.Member, *, name: str):
        guild_id = getattr(ctx.guild, 'id', None)
        user = self._get_user_data(member, guild_id=guild_id)

        if name not in user["achievements"]:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.error.achievement_missing",
                    default="❌ Achievement not found for this user.",
                )
            )
            return

        user["achievements"].remove(name)
        self.bot.db.save(guild_id=guild_id)

        await ctx.send(
            translate_for_ctx(
                ctx,
                "admin.msg.achievement_removed",
                default="🗑 Achievement '{name}' was removed from {member}.",
                name=name,
                member=member.mention,
            )
        )

    @commands.hybrid_command(description="Testping command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testping(self, ctx):
        latency_ms = round(getattr(self.bot, "latency", 0) * 1000)
        await ctx.send(
            translate_for_ctx(
                ctx,
                "admin.msg.ping_ok",
                default="🏓 Test OK — latency: **{latency} ms**",
                latency=latency_ms,
            )
        )

    @commands.hybrid_command(description="Testrank command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testrank(self, ctx, member: discord.Member = None):
        if member is None:
            await self._invoke_or_error(ctx, "rank")
            return
        await self._invoke_or_error(ctx, "rankuser", member=member)

    @commands.hybrid_command(description="Testcount command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testcount(self, ctx):
        ok_stats = await self._invoke_or_error(ctx, "countstats")
        ok_top = await self._invoke_or_error(ctx, "counttop")
        if ok_stats and ok_top:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.msg.count_test_complete",
                    default="✅ Count test complete.",
                )
            )

    @commands.hybrid_command(description="Testbirthday command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testbirthday(self, ctx, date: str = None):
        target_date = date or datetime.now().strftime("%d.%m")
        await self._invoke_or_error(ctx, "birthday", date=target_date)

    @commands.hybrid_command(description="Testpoll command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testpoll(self, ctx, duration: int = 45, *, question: str = "System test poll"):
        poll_cmd = self._cmd("poll")
        if poll_cmd is None:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.error.command_unavailable",
                    default="❌ Command not available: `{command}`",
                    command="poll",
                )
            )
            return
        if getattr(ctx, "is_ui_event_test", False):
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.msg.poll_ui_mode",
                    default=(
                        "✅ Poll test (UI mode): poll command found. "
                        "Interactive poll wizard skipped to avoid timeout in Event Tester."
                    ),
                )
            )
            return
        await ctx.send(
            translate_for_ctx(
                ctx,
                "admin.msg.poll_instructions",
                default=(
                    "ℹ️ `testpoll` uses the normal interactive poll wizard.\n"
                    "Provide this duration when asked: **{duration}** seconds\n"
                    "Suggested question: **{question}**"
                ),
                duration=max(10, min(duration, 3600)),
                question=question,
            )
        )
        await ctx.invoke(poll_cmd)

    @commands.hybrid_command(description="Testmusic command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testmusic(
        self,
        ctx,
        *,
        url: str = "https://www.youtube.com/watch?v=5jGWMtEhS1c",
    ):
        if not getattr(ctx.author, "voice", None) or not ctx.author.voice.channel:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.error.voice_required_testmusic",
                    default="❌ Join a voice channel first for `testmusic`.",
                )
            )
            return

        ok_join = await self._invoke_or_error(ctx, "join")
        if not ok_join:
            return
        ok_play = await self._invoke_or_error(ctx, "play", query=url)
        if ok_play:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.msg.music_test_started",
                    default="✅ Music test started: {url}",
                    url=url,
                )
            )

    @commands.hybrid_command(description="Testsay command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testsay(self, ctx, *, text: str = "✅ Test message from testsay"):
        await self._invoke_or_error(ctx, "say", text=text)

    @commands.hybrid_command(description="Testlevel command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testlevel(self, ctx, member: discord.Member, xp: int = 50):
        ok_add = await self._invoke_or_error(ctx, "addxp", member=member, amount=xp)
        if ok_add:
            await self._invoke_or_error(ctx, "rankuser", member=member)

    @commands.hybrid_command(description="Force one level-up and verify level-up message.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testlevelup(self, ctx, member: discord.Member, bonus_xp: int = 0):
        guild_id = getattr(ctx.guild, 'id', None)
        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        needed = max(1, self._xp_for_level(int(user.get("level", 1)), guild_id=guild_id) - int(user.get("xp", 0)))
        amount = needed + max(0, int(bonus_xp))

        ok_add = await self._invoke_or_error(ctx, "addxp", member=member, amount=amount)
        if ok_add:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.msg.level_forced",
                    default=(
                        "✅ Forced level-up for {member} with {amount} XP (needed: {needed}, bonus: {bonus})."
                    ),
                    member=member.mention,
                    amount=amount,
                    needed=needed,
                    bonus=max(0, int(bonus_xp)),
                )
            )
            await self._invoke_or_error(ctx, "rankuser", member=member)

    @commands.hybrid_command(description="Testlog command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testlog(self, ctx, category: str = "system", *, message: str = "Manual log test"):
        try:
            from data.logs.storage import database as logs_db

            logs_db.save_log(
                category,
                {
                    "type": "manual_test",
                    "user_id": getattr(ctx.author, "id", None),
                    "channel_id": getattr(ctx.channel, "id", None),
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.msg.log_written",
                    default="✅ Test log written (category: `{category}`). Check log channels/DB output.",
                    category=category,
                )
            )
        except Exception as exc:
            await ctx.send(
                translate_for_ctx(
                    ctx,
                    "admin.error.log_failed",
                    default="❌ Failed to write test log: {error}",
                    error=str(exc),
                )
            )


async def setup(bot):
    await bot.add_cog(AdminTools(bot))
