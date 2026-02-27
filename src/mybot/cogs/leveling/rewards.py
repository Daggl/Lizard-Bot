import discord
from discord.ext import commands

from .utils.level_config import get_level_rewards


class Rewards(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def check_rewards(self, member):

        user = self.bot.db.get_user(member.id)
        level = user["level"]
        level_rewards = get_level_rewards()

        if level in level_rewards:
            role_name = level_rewards[level]

            role = discord.utils.get(member.guild.roles, name=role_name)
            if role:
                await member.add_roles(role)


async def setup(bot):
    await bot.add_cog(Rewards(bot))
