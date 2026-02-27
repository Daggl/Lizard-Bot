import asyncio
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class AdminTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _cmd(self, name: str):
        return self.bot.get_command(name)

    async def _invoke_or_error(self, ctx, command_name: str, **kwargs):
        cmd = self._cmd(command_name)
        if cmd is None:
            await ctx.send(f"❌ Command not available: `{command_name}`")
            return False
        await ctx.invoke(cmd, **kwargs)
        return True

    def _get_user_data(self, member: discord.Member):
        return self.bot.db.get_user(member.id)

    @staticmethod
    def _xp_for_level(level: int) -> int:
        try:
            from mybot.cogs.leveling.utils.level_config import (
                get_level_base_xp,
                get_level_xp_step,
            )
        except Exception:
            from src.mybot.cogs.leveling.utils.level_config import (
                get_level_base_xp,
                get_level_xp_step,
            )

        base = max(0, int(get_level_base_xp()))
        step = max(0, int(get_level_xp_step()))
        return base + (int(level) * step)

    # XP GEBEN
    @commands.hybrid_command(description="Givexp command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def givexp(self, ctx, member: discord.Member, amount: int):

        user = self.bot.db.get_user(member.id)
        user["xp"] += amount
        self.bot.db.save()

        await ctx.send(f"✅ {member.mention} got {amount} XP.")

    # XP SETZEN
    @commands.hybrid_command(description="Setxp command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def setxp(self, ctx, member: discord.Member, amount: int):

        user = self.bot.db.get_user(member.id)
        user["xp"] = amount
        self.bot.db.save()

        await ctx.send(f"🛠 XP of {member.mention} set to {amount}.")

    # LEVEL SETZEN
    @commands.hybrid_command(description="Setlevel command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def setlevel(self, ctx, member: discord.Member, level: int):

        user = self.bot.db.get_user(member.id)
        user["level"] = level
        self.bot.db.save()

        await ctx.send(f"⭐ Level of {member.mention} set to {level}.")

    # ACHIEVEMENT TEST
    @commands.hybrid_command(description="Testachievement command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testachievement(self, ctx, member: discord.Member, *, name: str):

        user = self._get_user_data(member)

        if name in user["achievements"]:
            await ctx.send("❌ Achievement already exists.")
            return

        user["achievements"].append(name)
        self.bot.db.save()

        await ctx.send(f"🏆 Achievement '{name}' was given to {member.mention}.")

    @commands.hybrid_command(description="Giveachievement command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def giveachievement(self, ctx, member: discord.Member, *, name: str):
        user = self._get_user_data(member)

        if name in user["achievements"]:
            await ctx.send("❌ Achievement already exists.")
            return

        user["achievements"].append(name)
        self.bot.db.save()

        await ctx.send(f"🏆 Achievement '{name}' was given to {member.mention}.")

    @commands.hybrid_command(description="Removeachievement command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def removeachievement(self, ctx, member: discord.Member, *, name: str):
        user = self._get_user_data(member)

        if name not in user["achievements"]:
            await ctx.send("❌ Achievement not found for this user.")
            return

        user["achievements"].remove(name)
        self.bot.db.save()

        await ctx.send(f"🗑 Achievement '{name}' was removed from {member.mention}.")

    @commands.hybrid_command(description="Testping command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testping(self, ctx):
        latency_ms = round(getattr(self.bot, "latency", 0) * 1000)
        await ctx.send(f"🏓 Test OK — latency: **{latency_ms} ms**")

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
            await ctx.send("✅ Count test complete.")

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
            await ctx.send("❌ Command not available: `poll`")
            return
        if getattr(ctx, "is_ui_event_test", False):
            await ctx.send(
                "✅ Poll test (UI mode): poll command found. "
                "Interactive poll wizard skipped to avoid timeout in Event Tester."
            )
            return
        await ctx.send(
            "ℹ️ `testpoll` uses the normal interactive poll wizard.\n"
            f"Provide this duration when asked: **{max(10, min(duration, 3600))}** seconds\n"
            f"Suggested question: **{question}**"
        )
        await ctx.invoke(poll_cmd)

    @commands.hybrid_command(description="Testticketpanel command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testticketpanel(self, ctx):
        await self._invoke_or_error(ctx, "ticketpanel")

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
            await ctx.send("❌ Join a voice channel first for `testmusic`.")
            return

        ok_join = await self._invoke_or_error(ctx, "join")
        if not ok_join:
            return
        ok_play = await self._invoke_or_error(ctx, "play", query=url)
        if ok_play:
            await ctx.send(f"✅ Music test started: {url}")

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
        user = self.bot.db.get_user(member.id)
        needed = max(1, self._xp_for_level(int(user.get("level", 1))) - int(user.get("xp", 0)))
        amount = needed + max(0, int(bonus_xp))

        ok_add = await self._invoke_or_error(ctx, "addxp", member=member, amount=amount)
        if ok_add:
            await ctx.send(
                f"✅ Forced level-up for {member.mention} with {amount} XP "
                f"(needed: {needed}, bonus: {max(0, int(bonus_xp))})."
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
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await ctx.send(
                f"✅ Test log written (category: `{category}`). Check log channels/DB output."
            )
        except Exception as exc:
            await ctx.send(f"❌ Failed to write test log: {exc}")


async def setup(bot):
    await bot.add_cog(AdminTools(bot))
