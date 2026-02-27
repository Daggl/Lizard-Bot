import discord
from discord import app_commands
from discord.ext import commands

# ==========================================================
# ADMIN VIEW (ADMINS ONLY)
# ==========================================================


class AdminHelpView(discord.ui.View):

    def __init__(self, author):
        super().__init__(timeout=300)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ This menu does not belong to you.", ephemeral=True
            )
            return False

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Only administrators may use this menu.", ephemeral=True
            )
            return False

        return True

    # ======================================================
    # MAIN MENU
    # ======================================================

    @discord.ui.button(label="🏠 Main Menu", style=discord.ButtonStyle.primary)
    async def main_menu(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        embed = discord.Embed(
            title="🛠 Administrator Control Center",
            description=(
                "This menu gives you a complete overview\n"
                "of all admin features of the bot.\n\n"
                "Use the buttons to open detailed explanations.\n\n"
                "Open command: `/admin_help`\n"
                "Aliases: `/adminhelp`, `/ahelp`"
            ),
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="📊 Admin Tools",
            value="Bot control & manual interventions",
            inline=False,
        )

        embed.add_field(
            name="📁 Log System",
            value="Server monitoring & audit tracking",
            inline=False,
        )

        await interaction.response.edit_message(embed=embed)

    # ======================================================
    # ADMIN TOOLS DETAILLIERT
    # ======================================================

    @discord.ui.button(label="📊 Admin Tools", style=discord.ButtonStyle.danger)
    async def admin_tools(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        embed = discord.Embed(
            title="📊 Admin Control Commands", color=discord.Color.red()
        )

        embed.description = (
            "All commands below are admin-only and grouped by purpose."
        )

        embed.add_field(
            name="🧰 Messaging & Panels",
            value=(
                "`/say <text> [|image_url]`\n"
                "↳ Send a bot embed message (optional image with `|url`)\n\n"
                "`/adminpanel`\n"
                "↳ Open live admin status panel\n\n"
                "`/tempvoicepanel`\n"
                "↳ Post TempVoice control panel (admin-only)"
            ),
            inline=False,
        )

        embed.add_field(
            name="🏆 Leveling & XP",
            value=(
                "`/rankuser @user` ↳ Show rank card for target user\n"
                "`/addxp @user <amount>` ↳ Add XP + trigger normal checks\n"
                "`/removexp @user <amount>` ↳ Remove XP (not below 0)\n"
                "`/givexp @user <amount>` ↳ Direct admin XP utility\n"
                "`/setxp @user <amount>` ↳ Set exact XP value\n"
                "`/setlevel @user <level>` ↳ Set exact level\n"
                "`/reset @user` ↳ Reset leveling stats completely"
            ),
            inline=False,
        )

        embed.add_field(
            name="🏅 Achievements",
            value=(
                "`/giveachievement @user <name>` ↳ Add achievement manually\n"
                "`/removeachievement @user <name>` ↳ Remove achievement manually\n"
                "`/testachievement @user <name>` ↳ Test helper for achievement grant"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎫 Tickets & Polls",
            value=(
                "`/ticketpanel` ↳ Post ticket panel\n"
                "`/transcript <#channel>` ↳ Export transcript file\n"
                "`/close_ticket <#channel>` ↳ Force close ticket\n"
                "`/delete_poll <poll_id>` ↳ Delete poll from database"
            ),
            inline=False,
        )

        embed.add_field(
            name="🔢 Counting",
            value=(
                "`/countreset` ↳ Reset counting stats/data"
            ),
            inline=False,
        )

        await interaction.response.edit_message(embed=embed)

    # ======================================================
    # LOG SYSTEM DETAILLIERT
    # ======================================================

    @discord.ui.button(label="📁 Log System", style=discord.ButtonStyle.secondary)
    async def log_system(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        embed = discord.Embed(
            title="📁 Server Log System", color=discord.Color.orange()
        )

        embed.add_field(
            name="Chat Log Channel",
            value=(
                "• Message sent\n"
                "• Message deleted\n"
                "• Message edited\n"
                "• Audit log detection"
            ),
            inline=False,
        )

        embed.add_field(
            name="Moderation Log Channel",
            value=("• Kick\n" "• Ban\n" "• Timeout"),
            inline=False,
        )

        embed.add_field(
            name="Voice Log Channel",
            value=("• Voice join\n" "• Voice leave"),
            inline=False,
        )

        embed.add_field(
            name="Server Log Channel",
            value=(
                "• Channel created / deleted\n" "• Role changes\n" "• Nickname changed"
            ),
            inline=False,
        )

        embed.add_field(
            name="Member Log Channel",
            value=("• Member joined\n" "• Member left"),
            inline=False,
        )

        embed.add_field(
            name="Storage",
            value=(
                "All logs are additionally saved to the SQLite database "
                "``data/logs/logs.db`` for long-term storage.\n"
                "You can query or export logs with the helper script "
                "``tools/query_logs.py`` (recent, by-category, search, raw).\n"
                "Stored fields include type, user_id, channel_id,"
                " message, extra and timestamp."
            ),
            inline=False,
        )

        await interaction.response.edit_message(embed=embed)

    # ======================================================
    # TEST COMMANDS
    # ======================================================

    @discord.ui.button(label="🧪 Test Commands", style=discord.ButtonStyle.secondary)
    async def test_commands(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        embed = discord.Embed(title="🧪 Test Commands", color=discord.Color.green())

        embed.description = (
            "Use these commands to verify each major bot feature quickly.\n"
            "(Only where it makes practical sense.)"
        )

        embed.add_field(
            name="/testping",
            value="Checks bot responsiveness and shows current latency.",
            inline=False,
        )

        embed.add_field(
            name="/testwelcome",
            value="Tests the welcome flow with your own account.",
            inline=False,
        )

        embed.add_field(
            name="/testrank [@user]",
            value="Tests rank card rendering for yourself or a target user.",
            inline=False,
        )

        embed.add_field(
            name="/testcount",
            value="Runs counting feature checks (stats + leaderboard).",
            inline=False,
        )

        embed.add_field(
            name="/testbirthday [DD.MM]",
            value="Tests birthday save flow (uses today if no date is provided).",
            inline=False,
        )

        embed.add_field(
            name="/testpoll [seconds] [question]",
            value="Starts a guided poll smoke test via the normal poll wizard.",
            inline=False,
        )

        embed.add_field(
            name="/testticketpanel",
            value="Posts the ticket panel to validate ticket entry flow.",
            inline=False,
        )

        embed.add_field(
            name="/testmusic",
            value="Smoke-tests music voice pipeline (join + leave).",
            inline=False,
        )

        embed.add_field(
            name="/testsay [text]",
            value="Tests admin message/embed output.",
            inline=False,
        )

        embed.add_field(
            name="/testlevel @user [xp]",
            value="Tests leveling write + rank output in one command.",
            inline=False,
        )

        embed.add_field(
            name="/testachievement @user name",
            value="Tests manual achievement assignment.",
            inline=False,
        )

        embed.add_field(
            name="/testlog [category] [message]",
            value=(
                "Writes a manual test entry into the log database.\n"
                "Use event-based checks additionally for chat/voice/mod/server/member logs."
            ),
            inline=False,
        )

        await interaction.response.edit_message(embed=embed)


# ==========================================================
# COG
# ==========================================================


class AdminHelp(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="admin_help", aliases=["adminhelp", "ahelp"])
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def admin_help(self, ctx):

        embed = discord.Embed(
            title="🛠 Administrator Control Center",
            description=(
                "This menu is for administrators only.\n\n"
                "Here you get a full system overview.\n\n"
                "Command: `/admin_help`\n"
                "Aliases: `/adminhelp`, `/ahelp`"
            ),
            color=discord.Color.blue(),
        )

        view = AdminHelpView(ctx.author)
        await ctx.send(embed=embed, view=view)


# ==========================================================
# SETUP
# ==========================================================


async def setup(bot):
    await bot.add_cog(AdminHelp(bot))
