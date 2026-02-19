from discord.ext import commands
import discord
from mybot.cogs.leveling.utils.level_config import LEVEL_REWARDS

class Rewards(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def check_rewards(self, member):

        user = self.bot.db.get_user(member.id)
        level = user["level"]

        if level in LEVEL_REWARDS:
            role_name = LEVEL_REWARDS[level]

            role = discord.utils.get(member.guild.roles, name=role_name)
            if role:
                await member.add_roles(role)

async def setup(bot):
    await bot.add_cog(Rewards(bot))
