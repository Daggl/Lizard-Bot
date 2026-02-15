from discord.ext import commands
import math
from cogs.leveling.utils.database import Database
from cogs.leveling.utils.level_config import *

def xp_for_level(level):
    return 100 * level ** 2

class Levels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        bot.db = self.db  # global verfügbar machen

    async def add_xp(self, member, amount):
        user = self.db.get_user(member.id)
        user["xp"] += amount

        leveled = False

        while user["xp"] >= xp_for_level(user["level"]):
            user["xp"] -= xp_for_level(user["level"])
            user["level"] += 1
            leveled = True

            channel = self.bot.get_channel(ACHIEVEMENT_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"🎉 {member.mention} ist jetzt Level {user['level']}!"
                )

        if leveled:
            rewards_cog = self.bot.get_cog("Rewards")
            if rewards_cog:
                await rewards_cog.check_rewards(member)

        self.db.save()

async def setup(bot):
    await bot.add_cog(Levels(bot))
