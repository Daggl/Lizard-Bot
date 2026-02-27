import time

from discord.ext import commands, tasks

from .utils.level_config import (get_message_cooldown, get_voice_xp_per_minute,
                                 get_xp_per_message)


class Tracking(commands.Cog):
    """Tracks messages, voice time, and XP."""

    def __init__(self, bot):
        self.bot = bot

        # cooldowns for message xp
        self.cooldowns = {}

        # voice join timestamps
        self.voice_times = {}

        # start loops
        self.save_loop.start()
        self.voice_loop.start()  # FIX: new loop

    # ==========================================================
    # AUTO SAVE
    # ==========================================================

    @tasks.loop(minutes=1)
    async def save_loop(self):
        """Periodically save database."""
        self.bot.db.save()

    # ==========================================================
    # VOICE UPDATE LOOP (FIX)
    # ==========================================================

    @tasks.loop(minutes=1)
    async def voice_loop(self):
        """Update voice time every minute."""

        now = time.time()

        for user_id in list(self.voice_times.keys()):

            joined = self.voice_times[user_id]

            seconds = int(now - joined)

            if seconds <= 0:
                continue

            user = self.bot.db.get_user(user_id)

            user["voice_time"] += seconds

            xp = int((seconds / 60) * get_voice_xp_per_minute())

            levels = self.bot.get_cog("Levels")

            if levels and xp > 0:

                member = None

                for guild in self.bot.guilds:

                    member = guild.get_member(user_id)

                    if member:
                        break

                if member:
                    await levels.add_xp(member, xp)

            # reset timer
            self.voice_times[user_id] = now

    # ==========================================================
    # READY EVENT
    # ==========================================================

    @commands.Cog.listener()
    async def on_ready(self):
        """Restore voice timers."""

        now = time.time()

        for guild in self.bot.guilds:

            for voice_channel in guild.voice_channels:

                for member in voice_channel.members:

                    if not member.bot:

                        self.voice_times[member.id] = now

        print("[TRACKING] Voice timers restored")

    # ==========================================================
    # MESSAGE TRACKING
    # ==========================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        user_id = message.author.id
        now = time.time()

        if user_id in self.cooldowns:

            elapsed = now - self.cooldowns[user_id]

            if elapsed < get_message_cooldown():
                return

        self.cooldowns[user_id] = now

        db = self.bot.db
        user = db.get_user(user_id)

        user["messages"] += 1

        levels = self.bot.get_cog("Levels")

        if levels:
            await levels.add_xp(message.author, get_xp_per_message())

        achievements = self.bot.get_cog("Achievements")

        if achievements:
            await achievements.check_achievements(message.author)

    # ==========================================================
    # VOICE STATE UPDATE
    # ==========================================================

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        if member.bot:
            return

        db = self.bot.db

        before_channel = before.channel
        after_channel = after.channel

        # LEFT VOICE
        if before_channel and not after_channel:

            if member.id in self.voice_times:

                joined = self.voice_times.pop(member.id)

                seconds = int(time.time() - joined)

                if seconds > 0:

                    user = db.get_user(member.id)

                    user["voice_time"] += seconds

        # JOINED VOICE
        elif after_channel and not before_channel:

            self.voice_times[member.id] = time.time()

        # SWITCHED CHANNEL
        elif before_channel != after_channel:

            if member.id in self.voice_times:

                joined = self.voice_times.pop(member.id)

                seconds = int(time.time() - joined)

                if seconds > 0:

                    user = db.get_user(member.id)

                    user["voice_time"] += seconds

            self.voice_times[member.id] = time.time()

    # ==========================================================

    def cog_unload(self):

        self.save_loop.stop()
        self.voice_loop.stop()


# ==========================================================


async def setup(bot):

    await bot.add_cog(Tracking(bot))
