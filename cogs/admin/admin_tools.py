import discord
from discord.ext import commands


class AdminTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # XP GEBEN
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def givexp(self, ctx, member: discord.Member, amount: int):

        user = self.bot.db.get_user(member.id)
        user["xp"] += amount
        self.bot.db.save()

        await ctx.send(f"✅ {member.mention} got {amount} XP.")

    # XP SETZEN
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setxp(self, ctx, member: discord.Member, amount: int):

        user = self.bot.db.get_user(member.id)
        user["xp"] = amount
        self.bot.db.save()

        await ctx.send(f"🛠 XP of {member.mention} set to {amount}.")

    # LEVEL SETZEN
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlevel(self, ctx, member: discord.Member, level: int):

        user = self.bot.db.get_user(member.id)
        user["level"] = level
        self.bot.db.save()

        await ctx.send(f"⭐ Level of {member.mention} set to {level}.")

    # ACHIEVEMENT TEST
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def testachievement(self, ctx, member: discord.Member, *, name: str):

        user = self.bot.db.get_user(member.id)

        if name in user["achievements"]:
            await ctx.send("❌ Achievement already exists.")
            return

        user["achievements"].append(name)
        self.bot.db.save()

        await ctx.send(f"🏆 Achievement '{name}' was given to {member.mention}.")


async def setup(bot):
    await bot.add_cog(AdminTools(bot))
