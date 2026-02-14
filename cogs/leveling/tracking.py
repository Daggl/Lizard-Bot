from discord.ext import commands
import time
from utils.level_config import *

class Tracking(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.voice_times = {}

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

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        db = self.bot.db

        if after.channel and not before.channel:
            self.voice_times[member.id] = time.time()

        if before.channel and not after.channel:

            if member.id not in self.voice_times:
                return

            joined = self.voice_times.pop(member.id)
            seconds = int(time.time() - joined)

            user = db.get_user(member.id)
            user["voice_time"] += seconds

            levels = self.bot.get_cog("Levels")
            await levels.add_xp(member, (seconds / 60) * VOICE_XP_PER_MINUTE)

            ach = self.bot.get_cog("Achievements")
            await ach.check_achievements(member)

            db.save()

async def setup(bot):
    await bot.add_cog(Tracking(bot))
