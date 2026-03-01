"""Admin help / tutorial cog — interactive button-based admin command reference."""

import discord
from discord import app_commands
from discord.ext import commands

from mybot.utils.feature_flags import is_feature_enabled

# ==========================================================
# ADMIN VIEW (ADMINS ONLY)
# ==========================================================

ADMIN_HELP_TIMEOUT = 300


class AdminHelpView(discord.ui.View):
    """Interactive view with buttons for admin help sections."""

    def __init__(self, author, guild_id=None):
        super().__init__(timeout=ADMIN_HELP_TIMEOUT)
        self.author = author
        self.guild_id = guild_id

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

        _fe = lambda key: is_feature_enabled(self.guild_id, key)

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

        if _fe("leveling"):
            embed.add_field(
                name="🏆 Leveling & XP",
                value=(
                    "`/rankuser @user` ↳ Show rank card for target user\n"
                    "`/addxp @user <amount>` ↳ Add XP (positive only) + trigger checks\n"
                    "`/removexp @user <amount>` ↳ Remove XP (positive amount, not below 0)\n"
                    "`/givexp @user <amount>` ↳ Direct admin XP utility\n"
                    "`/setxp @user <amount>` ↳ Set exact XP value\n"
                    "`/setlevel @user <level>` ↳ Set exact level\n"
                    "`/reset @user` ↳ Reset leveling stats completely"
                ),
                inline=False,
            )

        if _fe("achievements"):
            embed.add_field(
                name="🏅 Achievements",
                value=(
                    "`/giveachievement @user <name>` ↳ Add achievement manually\n"
                    "`/removeachievement @user <name>` ↳ Remove achievement manually\n"
                    "`/testachievement @user <name>` ↳ Test helper for achievement grant"
                ),
                inline=False,
            )

        if _fe("tickets"):
            embed.add_field(
                name="🎫 Tickets",
                value=(
                    "`/ticketpanel` ↳ Post ticket panel\n"
                    "`/transcript <#channel>` ↳ Export transcript file\n"
                    "`/close_ticket <#channel>` ↳ Force close ticket"
                ),
                inline=False,
            )

        if _fe("polls"):
            embed.add_field(
                name="📊 Polls",
                value=(
                    "`/delete_poll <poll_id>` ↳ Delete poll from database"
                ),
                inline=False,
            )

        embed.add_field(
            name="🧹 Purge",
            value=(
                "`/purge @user [hours]` ↳ Delete user messages in current channel\n"
                "`/purgeall @user [hours]` ↳ Delete user messages in all channels\n"
                "↳ Also available in the Local UI with live progress"
            ),
            inline=False,
        )

        if _fe("counting"):
            embed.add_field(
                name="🔢 Counting",
                value=(
                    "`/countreset` ↳ Reset counting stats/data"
                ),
                inline=False,
            )

        if _fe("memes"):
            embed.add_field(
                name="😂 Memes",
                value=(
                    "`/meme create <name> <caption>` ↳ Save a meme from an attached image/GIF\n"
                    "`/meme show <name>` ↳ Display a saved meme\n"
                    "`/meme list` ↳ List all saved memes\n"
                    "`/meme delete <name>` ↳ Delete a meme (Admin)"
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
        if not is_feature_enabled(self.guild_id, "logging"):
            embed = discord.Embed(
                title="📁 Server Log System",
                description="⚠️ The logging feature is currently disabled on this server.",
                color=discord.Color.orange(),
            )
            await interaction.response.edit_message(embed=embed)
            return

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
                "``data/db/logs.db`` for long-term storage.\n"
                "Stored fields include type, user_id, channel_id,"
                " message, extra and timestamp.\n"
                "Log channels are configured **per guild** in the "
                "UI or directly in ``config/guilds/{guild_id}/log_*.json``."
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

        _fe = lambda key: is_feature_enabled(self.guild_id, key)

        # Test commands mapped to their feature key (None = always shown)
        test_cmds = [
            ("/testping", "Checks bot responsiveness and shows current latency.", None),
            ("/testwelcome", "Tests the welcome flow with your own account.", "welcome"),
            ("/testrank [@user]", "Tests rank card rendering for yourself or a target user.", "leveling"),
            ("/testcount", "Runs counting feature checks (stats + leaderboard).", "counting"),
            ("/testbirthday [DD.MM]", "Tests birthday save flow (uses today if no date is provided).", "birthdays"),
            ("/testpoll [seconds] [question]", "Starts a guided poll smoke test via the normal poll wizard.", "polls"),
            ("/testticketpanel", "Validates ticket system availability.", "tickets"),
            ("/testmusic", "Smoke-tests music voice pipeline (join + leave).", "music"),
            ("/testsay [text]", "Tests admin message/embed output.", None),
            ("/testlevel @user [xp]", "Tests leveling write + rank output in one command.", "leveling"),
            ("/testlevelup @user [bonus_xp]", "Forces at least one level-up and verifies level-up announcement output.", "leveling"),
            ("/testachievement @user name", "Tests manual achievement assignment.", "achievements"),
            ("/testlog [category] [message]", "Writes a manual test entry into the log database.", "logging"),
        ]

        for name, desc, fkey in test_cmds:
            if fkey is not None and not _fe(fkey):
                continue
            embed.add_field(name=name, value=desc, inline=False)

        await interaction.response.edit_message(embed=embed)


# ==========================================================
# COG
# ==========================================================


class AdminHelp(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="admin_help", aliases=["adminhelp", "ahelp"], description="Admin help command.")
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

        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        view = AdminHelpView(ctx.author, guild_id=guild_id)
        await ctx.send(embed=embed, view=view)


# ==========================================================
# SETUP
# ==========================================================


async def setup(bot):
    await bot.add_cog(AdminHelp(bot))
