import discord
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
                "Use the buttons to open detailed explanations."
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

        embed.add_field(
            name="*say",
            value=(
                "Makes the bot send a message.\n"
                "Syntax: *say #channel Message\n"
                "Attach image: add |link at the end of the message\n"
                "Example: *say Hello world!"
            ),
            inline=False,
        )

        embed.add_field(
            name="*adminpanel",
            value=(
                "Opens the status panel.\n\n"
                "Shows:\n"
                "• Bot ping & uptime\n"
                "• Loaded cogs\n"
                "• Server count\n"
                "• Level system status\n"
                "• Achievement status\n"
                "• Reward roles control\n"
            ),
            inline=False,
        )

        embed.add_field(
            name="*addxp @user amount",
            value=(
                "Manually add XP to a user.\n"
                "Used for tests or events.\n\n"
                "Automatically triggers:\n"
                "• Level up check\n"
                "• Achievement check\n"
                "• Reward roles check\n"
            ),
            inline=False,
        )

        embed.add_field(
            name="*removexp @user amount",
            value=(
                "Manually remove XP from a user.\n"
                "Useful for corrections or penalties.\n\n"
                "Will not reduce levels below 0."
            ),
            inline=False,
        )

        embed.add_field(
            name="*giveachievement @user achievementname",
            value=(
                "Grants an achievement to a user.\n"
                "Useful for special occasions or rewards.\n\n"
                "Example: *giveachievement @user First Kill"
            ),
            inline=False,
        )

        embed.add_field(
            name="*removeachievement @user achievementname",
            value=(
                "Removes an achievement from a user.\n"
                "Useful for corrections or penalties.\n\n"
                "Example: *removeachievement @user First Kill"
            ),
            inline=False,
        )

        embed.add_field(
            name="*reset @user",
            value="Resets a user's XP, level & achievements completely.",
            inline=False,
        )

        embed.add_field(
            name="*rankuser @user", value="Displays a user's rank.", inline=False
        )

        embed.add_field(
            name="*delete_poll <poll_id>",
            value=(
                "Deletes a poll from the database by its ID.\n"
                "Requires admin privileges."
            ),
            inline=False,
        )

        embed.add_field(
            name="*countreset",
            value=(
                "Resets the counting channel data and statistics.\n"
                "Requires admin privileges."
            ),
            inline=False,
        )

        embed.add_field(
            name="*givexp @user amount",
            value=(
                "Add XP to a user (alternative admin XP command).\n"
                "Useful for events and manual adjustments."
            ),
            inline=False,
        )

        embed.add_field(
            name="*setxp @user amount",
            value=(
                "Set a user's XP to a specific value.\n" "Requires admin privileges."
            ),
            inline=False,
        )

        embed.add_field(
            name="*setlevel @user level",
            value=(
                "Set a user's level to a specific value.\n" "Requires admin privileges."
            ),
            inline=False,
        )

        embed.add_field(
            name="*testachievement @user name",
            value=(
                "Grant a named achievement to a user for testing.\n"
                "Requires admin privileges."
            ),
            inline=False,
        )

        embed.add_field(
            name="*ticketpanel",
            value=(
                "Posts the ticket creation panel for users to open support tickets.\n"
                "Requires admin privileges."
            ),
            inline=False,
        )

        embed.add_field(
            name="*transcript <#channel>",
            value=(
                "Saves and returns a transcript for the specified ticket channel.\n"
                "Requires admin privileges."
            ),
            inline=False,
        )

        embed.add_field(
            name="*close_ticket <#channel>",
            value=(
                "Force-close and archive a ticket channel.\n"
                "Requires admin privileges."
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
                "All logs are additionally saved to the SQLite database `data/logs/logs.db` for long‑term storage.\n"
                "You can query or export logs with the helper script `tools/query_logs.py` (recent, by-category, search, raw).\n"
                "Stored fields include type, user_id, channel_id, message, extra and timestamp."
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

        embed.add_field(
            name="*ping",
            value="A simple test command to check the bot's responsiveness.",
            inline=False,
        )

        embed.add_field(
            name="*testwelcome", value="Tests the welcome system.", inline=False
        )

        await interaction.response.edit_message(embed=embed)


# ==========================================================
# COG
# ==========================================================


class AdminHelp(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="admin_help")
    @commands.has_permissions(administrator=True)
    async def admin_help(self, ctx):

        embed = discord.Embed(
            title="🛠 Administrator Control Center",
            description=(
                "This menu is for administrators only.\n\n"
                "Here you get a full system overview."
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
