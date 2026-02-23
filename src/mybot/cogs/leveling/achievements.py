from discord.ext import commands

from mybot.cogs.leveling.utils.level_config import *


class Achievements(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def check_achievements(self, member):

        db = self.bot.db
        user = db.get_user(member.id)

        for name, req in ACHIEVEMENTS.items():

            if name in user["achievements"]:
                continue

            valid = True

            for key, value in req.items():
                if user[key] < value:
                    valid = False

            if valid:
                user["achievements"].append(name)

                channel = self.bot.get_channel(ACHIEVEMENT_CHANNEL_ID)
                if channel:
                    await channel.send(
                        f"🏆 {member.mention} got Achievement **{name}**"
                    )

        db.save()


async def setup(bot):
    await bot.add_cog(Achievements(bot))
