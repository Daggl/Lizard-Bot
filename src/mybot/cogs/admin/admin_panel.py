import time

import discord
from discord.ext import commands

from mybot.cogs.leveling.utils.level_config import (get_achievement_channel_id,
                                                    get_achievements,
                                                    get_level_rewards)


class AdminPanelView(discord.ui.View):
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

    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    # -------------------------------------------------
    # EMBED ERSTELLEN
    # -------------------------------------------------
    async def create_panel_embed(self, guild):

        db = self.bot.db.data

        total_users = len(db)
        highest_level = 0
        total_achievements_given = 0

        for user in db.values():
            if user["level"] > highest_level:
                highest_level = user["level"]
            total_achievements_given += len(user["achievements"])

        uptime_seconds = int(time.time() - self.start_time)
        uptime = time.strftime("%Hh %Mm %Ss", time.gmtime(uptime_seconds))

        # Rollen Check
        reward_status = ""
        for lvl, role_name in get_level_rewards().items():
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                reward_status += f"Level {lvl} → {role_name} ✅\n"
            else:
                reward_status += f"Level {lvl} → {role_name} ❌ (Missing!)\n"

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
    @commands.command(name="adminpanel")
    @commands.has_permissions(administrator=True)
    async def adminpanel(self, ctx):

        embed = await self.create_panel_embed(ctx.guild)
        view = AdminPanelView(self)

        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(AdminPanel(bot))
