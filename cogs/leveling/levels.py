from discord.ext import commands
from cogs.leveling.utils.database import Database
from cogs.leveling.utils.level_config import *

# ======================================================
# XP FORMULA
# ======================================================

def xp_for_level(level: int) -> int:
    """
    XP required to advance FROM this level to next level.

    MEE6 style formula:
    smooth progression, no level 0 bug
    """

    return 100 + (level * 50)


# ======================================================
# LEVELS COG
# ======================================================

class Levels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

        # global access
        bot.db = self.db

    # ==================================================

    async def add_xp(self, member, amount: int):

        user = self.db.get_user(member.id)

        user["xp"] += int(amount)

        leveled = False

        # ==================================================
        # LEVEL LOOP
        # ==================================================

        while user["xp"] >= xp_for_level(user["level"]):

            needed = xp_for_level(user["level"])

            user["xp"] -= needed

            user["level"] += 1

            leveled = True

            # LEVEL UP MESSAGE
            channel = self.bot.get_channel(ACHIEVEMENT_CHANNEL_ID)

            if channel:

                await channel.send(
                    f"🎉 {member.mention} ist jetzt Level {user['level']}!"
                )

        # ==================================================
        # REWARDS
        # ==================================================

        if leveled:

            rewards_cog = self.bot.get_cog("Rewards")

            if rewards_cog:

                await rewards_cog.check_rewards(member)

        # ==================================================
        # SAVE
        # ==================================================

        self.db.save()


# ======================================================
# SETUP
# ======================================================

async def setup(bot):

    await bot.add_cog(Levels(bot))
