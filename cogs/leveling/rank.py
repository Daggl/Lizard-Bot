from discord.ext import commands
import discord


class Rank(commands.Cog):
    """Displays rank information and leaderboard."""

    def __init__(self, bot):
        self.bot = bot

    # ======================================================
    # USER COMMAND
    # ======================================================

    @commands.command()
    async def rank(self, ctx, member: discord.Member = None):
        """Show your rank or another user's rank."""

        member = member or ctx.author

        await self.send_rank_embed(ctx, member)

    # ======================================================
    # ADMIN COMMAND
    # ======================================================

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rankuser(self, ctx, member: discord.Member):
        """Admin: view rank of any user."""

        await self.send_rank_embed(ctx, member)

    # ======================================================
    # EMBED FUNCTION
    # ======================================================

    async def send_rank_embed(self, ctx, member):

        user = self.bot.db.get_user(member.id)

        if not user:
            await ctx.send("Keine Daten gefunden.")
            return

        achievements = user.get("achievements", [])

        embed = discord.Embed(
            title=f"Rank von {member.display_name}",
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="Level",
            value=user.get("level", 0)
        )

        embed.add_field(
            name="XP",
            value=user.get("xp", 0)
        )

        embed.add_field(
            name="Nachrichten",
            value=user.get("messages", 0)
        )

        embed.add_field(
            name="Voice Minuten",
            value=user.get("voice_time", 0) // 60
        )

        embed.add_field(
            name="Achievements",
            value=", ".join(achievements) if achievements else "Keine",
            inline=False
        )

        await ctx.send(embed=embed)

    # ======================================================
    # LEADERBOARD
    # ======================================================

    @commands.command()
    async def leaderboard(self, ctx):
        """Show top 10 users."""

        data = self.bot.db.data

        sorted_users = sorted(
            data.items(),
            key=lambda x: (x[1].get("level", 0), x[1].get("xp", 0)),
            reverse=True
        )[:10]

        lines = []

        for i, (user_id, user) in enumerate(sorted_users, start=1):

            member = ctx.guild.get_member(int(user_id))

            name = member.display_name if member else "Unknown"

            level = user.get("level", 0)

            lines.append(f"{i}. {name} — Level {level}")

        embed = discord.Embed(
            title="🏆 Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)


# ======================================================
# SETUP
# ======================================================

async def setup(bot):
    await bot.add_cog(Rank(bot))
