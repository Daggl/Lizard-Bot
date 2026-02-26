import discord
from discord.ext import commands

from mybot.cogs.leveling.utils.database import Database
from mybot.cogs.leveling.utils.level_config import (
    ACHIEVEMENT_CHANNEL_ID,
    EMOJI_WIN,
    EMOJI_HEART,
    get_message_templates,
)

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
                try:
                    level_up_tpl, _ = get_message_templates()
                    description = str(level_up_tpl).format(
                        member_mention=member.mention,
                        member_name=getattr(member, "name", member.display_name),
                        member_display_name=member.display_name,
                        member_id=member.id,
                        guild_name=getattr(getattr(member, "guild", None), "name", ""),
                        level=user["level"],
                        emoji_win=EMOJI_WIN,
                        emoji_heart=EMOJI_HEART,
                    )
                except Exception:
                    description = (
                        f"{EMOJI_WIN} {member.mention}\n"
                        f"you just reached level {user['level']}!\n"
                        f"keep it up, cutie! {EMOJI_HEART}"
                    )

                embed = discord.Embed(
                    description=description,
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
