from discord.ext import commands
import discord


class HelpTutorial(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        bot.remove_command("help")  # Standard Help entfernen

    @commands.command(name="help")
    async def h(self, ctx):

        embed = discord.Embed(
            title="🤖 Bot Hilfe & Tutorials",
            description="Hier findest du alle Funktionen erklärt",
            color=discord.Color.blurple()
        )

        # ---------------------------
        # LEVEL SYSTEM
        # ---------------------------
        embed.add_field(
            name="🏆 Level System",
            value=(
                "**Wie funktioniert es?**\n"
                "• Du bekommst XP durch Schreiben und Voice Chat\n"
                "• Höhere Level geben Rollen & Belohnungen\n\n"

                "**Commands:**\n"
                "`*rank` → Zeigt deinen Fortschritt\n"
                "`*leaderboard` → Server Rangliste"
            ),
            inline=False
        )

        # ---------------------------
        # UMFRAGEN
        # ---------------------------
        embed.add_field(
            name="📊 Umfragen",
            value=(
                "**Erstellt Abstimmungen für den Server**\n\n"
                "`*umfrage <Frage>`\n"
                "➡ Beispiel:\n"
                "`*umfrage Mögt ihr Pizza?`"
            ),
            inline=False
        )

        # ---------------------------
        # GEBURTSTAGE
        # ---------------------------
        embed.add_field(
            name="🎂 Geburtstage",
            value=(
                "**Speichert deinen Geburtstag**\n\n"
                "`*geburtstag <TT.MM>`\n"
                "➡ Der Bot erinnert automatisch"
            ),
            inline=False
        )

        # ---------------------------
        # XP SYSTEM ERKLÄRUNG
        # ---------------------------
        embed.add_field(
            name="⭐ XP verdienen",
            value=(
                "Du bekommst XP durch:\n"
                "• Nachrichten schreiben\n"
                "• Voice Chat Zeit\n"
                "• Achievements freischalten"
            ),
            inline=False
        )

        # ---------------------------
        # ACHIEVEMENTS
        # ---------------------------
        embed.add_field(
            name="🏅 Achievements",
            value=(
                "Achievements sind Erfolge die du freischalten kannst.\n\n"
                "Beispiele:\n"
                "• Viele Nachrichten schreiben\n"
                "• Lange im Voice bleiben\n"
                "• Hohe Level erreichen"
            ),
            inline=False
        )

        # ---------------------------
        # ALLGEMEIN
        # ---------------------------
        embed.add_field(
            name="⚙ Allgemein",
            value=(
                "`*ping` → Testet ob der Bot online ist\n"
                "`*hilfe` → Zeigt dieses Menü"
            ),
            inline=False
        )

        embed.set_footer(text="Mehr Features folgen später 👀")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpTutorial(bot))
