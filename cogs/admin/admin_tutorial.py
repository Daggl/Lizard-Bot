import discord
from discord.ext import commands

# ==========================================================
# ADMIN VIEW (NUR ADMINS)
# ==========================================================

class AdminHelpView(discord.ui.View):

    def __init__(self, author):
        super().__init__(timeout=300)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ Dieses Menü gehört nicht dir.",
                ephemeral=True
            )
            return False

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren dürfen dieses Menü nutzen.",
                ephemeral=True
            )
            return False

        return True

    # ======================================================
    # HAUPTMENÜ
    # ======================================================

    @discord.ui.button(label="🏠 Hauptmenü", style=discord.ButtonStyle.primary)
    async def main_menu(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(
            title="🛠 Administrator Kontrollzentrum",
            description=(
                "Dieses Menü bietet dir eine vollständige Übersicht\n"
                "über alle Admin Funktionen des Bots.\n\n"
                "Nutze die Buttons, um detaillierte Erklärungen zu öffnen."
            ),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="📊 Admin Tools",
            value="Bot Kontrolle & manuelle Eingriffe",
            inline=False
        )

        embed.add_field(
            name="📁 Log System",
            value="Serverüberwachung & Audit Tracking",
            inline=False
        )

 
        await interaction.response.edit_message(embed=embed)

    # ======================================================
    # ADMIN TOOLS DETAILLIERT
    # ======================================================

    @discord.ui.button(label="📊 Admin Tools", style=discord.ButtonStyle.danger)
    async def admin_tools(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(
            title="📊 Admin Kontrollbefehle",
            color=discord.Color.red()
        )

        embed.add_field(
            name="*say",
            value=(
             "Lässt den Bot eine Nachricht senden.\n"
            "Syntax: *say #channel Nachricht\n"
            "Bild anhängen: |link am Ende der Nachricht\n"
             "Beispiel: *say Hallo Welt!"
),
            inline=False
        )

        embed.add_field(
            name="*adminpanel",
            value=(
                "Öffnet das Statuspanel.\n\n"
                "Zeigt:\n"
                "• Bot Ping & Uptime\n"
                "• Geladene Cogs\n"
                "• Server Anzahl\n"
                "• Level System Status\n"
                "• Achievement Status\n"
                "• Reward Rollen Kontrolle\n"
            ),
            inline=False
        )

        embed.add_field(
            name="*addxp @user menge",
            value=(
                "Manuelle XP Vergabe.\n"
                "Wird genutzt für Tests oder Events.\n\n"
                "Löst automatisch:\n"
                "• Level Up Check\n"
                "• Achievement Check\n"
                "• Reward Rollen Check"
            ),
            inline=False
        )

        embed.add_field(
            name="*removexp",
            value="Entfernt XP. Führt keine negativen Level unter 0 aus.",
            inline=False
        )

        embed.add_field(
            name="*resetuser",
            value="Setzt XP, Level & Achievements vollständig zurück.",
            inline=False
        )

        embed.add_field(
            name="*rankuser @user",
            value="Zeigt den Rang eines Benutzers an.",
            inline=False
        )

        await interaction.response.edit_message(embed=embed)

 
    # ======================================================
    # LOG SYSTEM DETAILLIERT
    # ======================================================

    @discord.ui.button(label="📁 Log System", style=discord.ButtonStyle.secondary)
    async def log_system(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(
            title="📁 Server Log System",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="Chat Log Channel",
            value=(
                "• Nachricht gesendet\n"
                "• Nachricht gelöscht\n"
                "• Nachricht bearbeitet\n"
                "• Audit Log Erkennung"
            ),
            inline=False
        )

        embed.add_field(
            name="Moderation Log Channel",
            value=(
                "• Kick\n"
                "• Ban\n"
                "• Timeout"
            ),
            inline=False
        )

        embed.add_field(
            name="Voice Log Channel",
            value=(
            "• Voice Join\n"
            "• Voice Leave"
            ),
            inline=False
        )

        embed.add_field(
            name="Server Log Channel",
            value=(
                "• Channel erstellt / gelöscht\n"
                "• Rollen Änderungen\n"
                "• Nickname geändert"
            ),
            inline=False
        )

        embed.add_field(
            name="Member Log Channel",
            value=(
                "• Member beigetreten\n"
                "• Member verlassen"
            ),
            inline=False
        )

        embed.add_field(
            name="Speicherung",
            value=(
                "Alle Logs werden zusätzlich in logs.json gespeichert.\n"
                "Automatische Rotation verhindert Überlastung."
            ),
            inline=False
        )

        await interaction.response.edit_message(embed=embed)

    # ======================================================
    # TEST COMMANDS
    # ======================================================

    @discord.ui.button(label="🧪 Test Commands", style=discord.ButtonStyle.secondary)
    async def test_commands(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(
            title="🧪 Test Commands",
            color=discord.Color.green()
        )

        embed.add_field(
            name="*ping",
            value="Ein einfacher Test Command um die Reaktionsfähigkeit des Bots zu prüfen.",
            inline=False
        )

        embed.add_field(
            name="*testwelcome",
            value="Testet das Willkommenssystem.",
            inline=False
        )

        await interaction.response.edit_message(embed=embed)


# ==========================================================
# COG
# ==========================================================

class AdminHelp(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="adminhilfe")
    @commands.has_permissions(administrator=True)
    async def admin_help(self, ctx):

        embed = discord.Embed(
            title="🛠 Administrator Kontrollzentrum",
            description=(
                "Dieses Menü ist ausschließlich für Administratoren.\n\n"
                "Hier erhältst du eine vollständige Systemübersicht."
            ),
            color=discord.Color.blue()
        )

        view = AdminHelpView(ctx.author)
        await ctx.send(embed=embed, view=view)

# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):
    await bot.add_cog(AdminHelp(bot))
