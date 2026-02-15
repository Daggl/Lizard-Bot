import discord
from discord.ext import commands
import time
from cogs.leveling.utils.level_config import LEVEL_REWARDS, ACHIEVEMENTS, ACHIEVEMENT_CHANNEL_ID


class AdminPanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self.cog = cog

    @discord.ui.button(label="🔄 Aktualisieren", style=discord.ButtonStyle.green)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        for lvl, role_name in LEVEL_REWARDS.items():
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                reward_status += f"Level {lvl} → {role_name} ✅\n"
            else:
                reward_status += f"Level {lvl} → {role_name} ❌ (Fehlt!)\n"

        embed = discord.Embed(
            title="🛠 Admin Status Panel",
            color=discord.Color.red()
        )

        # BOT STATUS
        embed.add_field(
            name="🤖 Bot Status",
            value=(
                f"Ping: {round(self.bot.latency * 1000)}ms\n"
                f"Uptime: {uptime}\n"
                f"Geladene Cogs: {len(self.bot.cogs)}\n"
                f"Server: {len(self.bot.guilds)}"
            ),
            inline=False
        )

        # LEVEL SYSTEM
        embed.add_field(
            name="🏆 Level System",
            value=(
                f"Gespeicherte User: {total_users}\n"
                f"Höchstes Level: {highest_level}"
            ),
            inline=False
        )

        # ACHIEVEMENTS
        embed.add_field(
            name="🏅 Achievements",
            value=(
                f"Definiert: {len(ACHIEVEMENTS)}\n"
                f"Vergeben: {total_achievements_given}\n"
                f"Channel ID: {ACHIEVEMENT_CHANNEL_ID}"
            ),
            inline=False
        )

        # REWARDS CHECK
        embed.add_field(
            name="🎁 Rewards Check",
            value=reward_status or "Keine Rewards definiert",
            inline=False
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
