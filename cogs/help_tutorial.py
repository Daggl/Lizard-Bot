import discord

from discord.ext import commands


class HelpTutorial(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        bot.remove_command("help")

    @commands.command(name="help")
    async def h(self, ctx):

        embed = discord.Embed(
            title="🤖 Bot Help & Tutorials",
            description="Here you can find all features explained",
            color=discord.Color.blurple()
        )

        # ---------------------------
        # LEVEL SYSTEM
        # ---------------------------

        embed.add_field(
            name="🏆 Level System",
            value=(
                "**How does it work?**\n"
                "• You gain XP by chatting and voice chat\n"
                "• Higher levels give roles & rewards\n\n"
                "**Commands:**\n"
                "`*rank` → Shows your progress\n"
                "`*leaderboard` → Server leaderboard"
            ),
            inline=False
        )

        # ---------------------------
        # POLLS
        # ---------------------------

        embed.add_field(
            name="📊 Polls",
            value=(
                "**Create polls for the server**\n\n"
                "`*poll <question>`\n"
                "➡ Example:\n"
                "`*poll Do you like pizza?`"
            ),
            inline=False
        )

        # ---------------------------
        # BIRTHDAYS
        # ---------------------------

        embed.add_field(
            name="🎂 Birthdays",
            value=(
                "**Save your birthday**\n\n"
                "`*birthday <DD.MM>`\n"
                "➡ The bot will remind automatically"
            ),
            inline=False
        )

        # ---------------------------
        # XP SYSTEM
        # ---------------------------

        embed.add_field(
            name="⭐ Earn XP",
            value=(
                "You gain XP by:\n"
                "• Sending messages\n"
                "• Voice chat time\n"
                "• Unlocking achievements"
            ),
            inline=False
        )

        # ---------------------------
        # ACHIEVEMENTS
        # ---------------------------

        embed.add_field(
            name="🏅 Achievements",
            value=(
                "Achievements are milestones you can unlock.\n\n"
                "Examples:\n"
                "• Sending many messages\n"
                "• Staying long in voice chat\n"
                "• Reaching high levels"
            ),
            inline=False
        )

        # ---------------------------
        # GENERAL
        # ---------------------------

        embed.add_field(
            name="⚙ General",
            value=(
                "`*ping` → Tests if the bot is online\n"
                "`*help` → Shows this menu"
            ),
            inline=False
        )

        # ---------------------------
        # MISC & FUN
        # ---------------------------

        embed.add_field(
            name="🧪 Misc & Fun",
            value=(
                "`*insult <name>` → Fun: insult someone\n"
                "`*secretinsult <name>` → Send an insult but replies ephemeral"
            ),
            inline=False
        )

        # ---------------------------
        # COUNTING
        # ---------------------------

        embed.add_field(
            name="🔢 Counting",
            value=(
                "`*countstats` → Show counting channel statistics\n"
                "`*counttop` → Show counting leaderboard"
            ),
            inline=False
        )

        embed.set_footer(
            text="More features coming later 👀"
        )

        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(HelpTutorial(bot))
