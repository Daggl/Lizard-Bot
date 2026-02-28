"""Admin status panel cog — live overview of bot health, leveling and rewards."""

import time

import discord
from discord import app_commands
from discord.ext import commands

try:
    from ..leveling.utils.level_config import (get_achievement_channel_id,
                                               get_achievements, get_level_rewards)
except Exception:
    # Graceful fallback if leveling cog is not installed
    def get_achievement_channel_id(guild_id=None): return 0
    def get_achievements(guild_id=None): return {}
    def get_level_rewards(guild_id=None): return {}


def _format_uptime(seconds: int) -> str:
    """Return a human-readable uptime string that handles >24 h correctly."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    parts.append(f"{hours}h {minutes}m {secs}s")
    return " ".join(parts)


class AdminPanelView(discord.ui.View):
    """Persistent view attached to the admin panel embed."""

    def __init__(self, cog):
        super().__init__(timeout=120)
        self.cog = cog

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.green)
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = await self.cog.create_panel_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)


class AdminPanel(commands.Cog):
    """Provides a live admin status panel showing bot health, leveling stats and reward checks."""

    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    async def create_panel_embed(self, guild) -> discord.Embed:
        """Build the admin panel embed with current stats."""
        db = getattr(getattr(self.bot, "db", None), "data", None) or {}

        total_users = len(db)
        highest_level = 0
        total_achievements_given = 0

        for user in db.values():
            highest_level = max(highest_level, user.get("level", 0))
            total_achievements_given += len(user.get("achievements", []))

        uptime_seconds = int(time.time() - self.start_time)
        uptime = _format_uptime(uptime_seconds)

        # Check reward roles
        reward_lines: list[str] = []
        for lvl, role_name in get_level_rewards().items():
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                reward_lines.append(f"Level {lvl} → {role_name} ✅")
            else:
                reward_lines.append(f"Level {lvl} → {role_name} ❌ (Missing!)")
        reward_status = "\n".join(reward_lines)

        embed = discord.Embed(title="🛠 Admin Status Panel", color=discord.Color.red())

        # BOT STATUS
        embed.add_field(
            name="🤖 Bot Status",
            value=(
                f"Ping: {round(self.bot.latency * 1000)}ms\n"
                f"Uptime: {uptime}\n"
                f"Loaded Cogs: {len(self.bot.cogs)}\n"
                f"Server: {len(self.bot.guilds)}"
            ),
            inline=False,
        )

        # LEVEL SYSTEM
        embed.add_field(
            name="🏆 Level System",
            value=(f"Saved User: {total_users}\n" f"Highest Level: {highest_level}"),
            inline=False,
        )

        # ACHIEVEMENTS
        embed.add_field(
            name="🏅 Achievements",
            value=(
                f"Defined: {len(get_achievements())}\n"
                f"Given: {total_achievements_given}\n"
                f"Channel ID: {get_achievement_channel_id()}"
            ),
            inline=False,
        )

        # REWARDS CHECK
        embed.add_field(
            name="🎁 Rewards Check",
            value=reward_status or "No Rewards defined",
            inline=False,
        )

        embed.set_footer(text="Admin Panel • Live Status")

        return embed

    # -------------------------------------------------
    # COMMAND
    # -------------------------------------------------
    @commands.hybrid_command(name="adminpanel", description="Show live admin status panel.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def adminpanel(self, ctx):
        """Display the admin panel embed with a refresh button."""
        embed = await self.create_panel_embed(ctx.guild)
        view = AdminPanelView(self)

        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(AdminPanel(bot))
