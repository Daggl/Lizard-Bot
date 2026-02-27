import discord
from discord.ext import commands


class HelpTutorial(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        bot.remove_command("help")

    @commands.command(name="help", aliases=["tutorial", "hilfe"])
    async def h(self, ctx):

        embed = discord.Embed(
            title="🤖 Bot Help & Tutorials",
            description=(
                "Here you can find all features explained.\n\n"
                "Command: `*help`\n"
                "Aliases: `*tutorial`, `*hilfe`"
            ),
            color=discord.Color.blurple(),
        )

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
            inline=False,
        )

        embed.add_field(
            name="📊 Polls",
            value=(
                "**Create polls for the server**\n\n"
                "`*poll <question>`\n"
                "➡ Example:\n"
                "`*poll Do you like pizza?`"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎂 Birthdays",
            value=(
                "**Save your birthday**\n\n"
                "`*birthday <DD.MM>`\n"
                "➡ The bot will remind automatically"
            ),
            inline=False,
        )

        embed.add_field(
            name="⭐ Earn XP",
            value=(
                "You gain XP by:\n"
                "• Sending messages\n"
                "• Voice chat time\n"
                "• Unlocking achievements"
            ),
            inline=False,
        )

        embed.add_field(
            name="🏅 Achievements",
            value=(
                "Achievements are milestones you can unlock.\n\n"
                "Examples:\n"
                "• Sending many messages\n"
                "• Staying long in voice chat\n"
                "• Reaching high levels"
            ),
            inline=False,
        )

        embed.add_field(
            name="⚙ General",
            value=(
                "`*ping` → Tests if the bot is online\n"
                "`*help` → Shows this menu\n"
                "`*tutorial` / `*hilfe` → Aliases for help\n"
                "`*admin_help` → Opens admin command center"
            ),
            inline=False,
        )

        embed.add_field(
            name="🧪 Misc & Fun",
            value=(
                "`*insult <name>` → Fun: insult someone\n"
                "`*secretinsult <name>` → Send an insult but replies ephemeral"
            ),
            inline=False,
        )

        embed.add_field(
            name="🔢 Counting",
            value=(
                "`*countstats` → Show counting channel statistics\n"
                "`*counttop` → Show counting leaderboard"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎫 Tickets",
            value=(
                "`*ticket` — Open a private support ticket"
                " (or use the ticket panel posted by staff)"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎙️ TempVoice",
            value=(
                "Create temporary voice channels automatically.\n\n"
                "- Join the configured TempVoice create channel\n"
                "- The bot creates your own channel and moves you there\n"
                "- Channel is deleted automatically when everyone leaves\n"
                "- Management is done via TempVoice panel buttons posted by admins"
                " (lock/unlock, hide/unhide, rename, limit, transfer, claim, delete)"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎵 Music",
            value=(
                "Play music from YouTube or import Spotify tracks/playlists.\n\n"
                "`*join` → Bot joins your voice channel\n"
                "`*play <query|YouTube URL>` → Play or search YouTube\n"
                "`*skip` → Skip current track\n"
                "`*queue` → Show queue\n"
                "`*now` → Show now playing\n"
                "`*stop` → Stop and clear queue\n"
                "`*spotify <url> [max_tracks]` → Import Spotify track or playlist\n"
                "into the queue."
            ),
            inline=False,
        )

        embed.set_footer(text="More features coming later 👀")

        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(HelpTutorial(bot))
