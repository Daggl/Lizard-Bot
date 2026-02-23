import discord
from discord.ext import commands

from mybot.cogs.leveling.utils.database import Database
from mybot.cogs.leveling.utils.level_config import ACHIEVEMENT_CHANNEL_ID

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

                embed = discord.Embed(
                    description=(
                        f" \n\n"
                        f"<:gg_wp:1473709030839943189> "
                        f"{member.mention}\n"
                        f"you just reached level {user['level']}!\n "
                        f"keep it up, cutie! "
                        f"<a:AP_scribbleheart:1472809672946745519>"
                    ),
                    color=0x5865F2,
                )

                embed.set_thumbnail(url=member.display_avatar.url)

                await channel.send(embed=embed)

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
