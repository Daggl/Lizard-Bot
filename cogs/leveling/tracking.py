from discord.ext import commands
import time
from cogs.leveling.utils.level_config import *


class Tracking(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.voice_times = {}

    # ======================================================
    # MESSAGE TRACKING
    # ======================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        db = self.bot.db
        user = db.get_user(message.author.id)

        now = time.time()

        if message.author.id in self.cooldowns:
            if now - self.cooldowns[message.author.id] < MESSAGE_COOLDOWN:
                return

        self.cooldowns[message.author.id] = now

        user["messages"] += 1

        levels = self.bot.get_cog("Levels")
        await levels.add_xp(message.author, XP_PER_MESSAGE)

        ach = self.bot.get_cog("Achievements")
        await ach.check_achievements(message.author)

        db.save()

    # ======================================================
    # VOICE TRACKING
    # ======================================================

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        db = self.bot.db

        # USER LEAVES OR SWITCHES CHANNEL
        if before.channel:

            if member.id in self.voice_times:

                joined = self.voice_times.pop(member.id)
                seconds = int(time.time() - joined)

                user = db.get_user(member.id)
                user["voice_time"] += seconds

                levels = self.bot.get_cog("Levels")
                await levels.add_xp(
                    member,
                    (seconds / 60) * VOICE_XP_PER_MINUTE
                )

                ach = self.bot.get_cog("Achievements")
                await ach.check_achievements(member)

                db.save()

        # USER SWITCH CHANNEL → restart timer
        if after.channel:
            self.voice_times[member.id] = time.time()


    @commands.Cog.listener()
    async def on_ready(self):

        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    self.voice_times[member.id] = time.time()


# ======================================================
# SETUP
# ======================================================

async def setup(bot):
    await bot.add_cog(Tracking(bot))
