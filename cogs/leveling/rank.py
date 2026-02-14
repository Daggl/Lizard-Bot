from discord.ext import commands
import discord

class Rank(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def rank(self, ctx, member: discord.Member = None):

        member = member or ctx.author
        user = self.bot.db.get_user(member.id)

        embed = discord.Embed(title=f"Rank von {member.name}")
        embed.add_field(name="Level", value=user["level"])
        embed.add_field(name="XP", value=user["xp"])
        embed.add_field(name="Nachrichten", value=user["messages"])
        embed.add_field(name="Voice Minuten", value=user["voice_time"] // 60)
        embed.add_field(
            name="Achievements",
            value=", ".join(user["achievements"]) or "Keine"
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx):

        data = self.bot.db.data

        sorted_users = sorted(
            data.items(),
            key=lambda x: x[1]["level"],
            reverse=True
        )[:10]

        text = ""

        for i, (user_id, user) in enumerate(sorted_users, 1):
            member = ctx.guild.get_member(int(user_id))
            name = member.name if member else "Unknown"
            text += f"{i}. {name} - Level {user['level']}\n"

        embed = discord.Embed(title="🏆 Leaderboard", description=text)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Rank(bot))
