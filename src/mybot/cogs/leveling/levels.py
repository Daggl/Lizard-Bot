import discord
from discord.ext import commands

from mybot.cogs.leveling.utils.database import Database
from mybot.cogs.leveling.utils.level_config import (
    ACHIEVEMENT_CHANNEL_ID,
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
                    level_up_tpl, _achievement_tpl, win_emoji, heart_emoji = get_message_templates()
                    template_raw = str(level_up_tpl)
                    includes_win = ("{emoji_win}" in template_raw) or ("{leading_emoji}" in template_raw)
                    includes_heart = ("{emoji_heart}" in template_raw) or ("{trailing_emoji}" in template_raw)
                    description = template_raw.format(
                        member_mention=member.mention,
                        member_name=getattr(member, "name", member.display_name),
                        member_display_name=member.display_name,
                        member_id=member.id,
                        guild_name=getattr(getattr(member, "guild", None), "name", ""),
                        level=user["level"],
                        emoji_win=win_emoji,
                        emoji_heart=heart_emoji,
                        leading_emoji=win_emoji,
                        trailing_emoji=heart_emoji,
                    )
                    if win_emoji and not includes_win:
                        description = f"{win_emoji} {description}".strip()
                    if heart_emoji and not includes_heart:
                        description = f"{description} {heart_emoji}".strip()
                except Exception:
                    description = (
                        f"{member.mention}\n"
                        f"you just reached level {user['level']}!\n"
                        f"keep it up, cutie!"
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
