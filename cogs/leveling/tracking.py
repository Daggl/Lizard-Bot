from discord.ext import commands, tasks
import time

from cogs.leveling.utils.level_config import (
    MESSAGE_COOLDOWN,
    XP_PER_MESSAGE,
    VOICE_XP_PER_MINUTE
)


class Tracking(commands.Cog):
    """Tracks messages, voice time, and XP."""

    def __init__(self, bot):
        self.bot = bot

        # cooldowns for message xp
        self.cooldowns = {}

        # voice join timestamps
        self.voice_times = {}

        # start autosave loop
        self.save_loop.start()

    # ==========================================================
    # AUTO SAVE EVERY 5 MINUTES
    # ==========================================================

    @tasks.loop(minutes=5)
    async def save_loop(self):
        """Periodically save database to prevent data loss."""
        self.bot.db.save()

    # ==========================================================
    # READY EVENT
    # ==========================================================

    @commands.Cog.listener()
    async def on_ready(self):
        """Restore voice timers for users already in voice."""

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
        """Track messages and give XP."""

        if message.author.bot:
            return

        user_id = message.author.id
        now = time.time()

        # cooldown check
        if user_id in self.cooldowns:

            elapsed = now - self.cooldowns[user_id]

            if elapsed < MESSAGE_COOLDOWN:
                return

        self.cooldowns[user_id] = now

        db = self.bot.db
        user = db.get_user(user_id)

        user["messages"] += 1

        # add xp
        levels = self.bot.get_cog("Levels")

        if levels:
            await levels.add_xp(message.author, XP_PER_MESSAGE)

        # check achievements
        achievements = self.bot.get_cog("Achievements")

        if achievements:
            await achievements.check_achievements(message.author)

    # ==========================================================
    # VOICE TRACKING
    # ==========================================================

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Track voice time and give XP."""

        if member.bot:
            return

        db = self.bot.db

        before_channel = before.channel
        after_channel = after.channel

        # ======================================================
        # USER LEFT VOICE
        # ======================================================

        if before_channel and not after_channel:

            if member.id in self.voice_times:

                joined = self.voice_times.pop(member.id)

                seconds = int(time.time() - joined)

                user = db.get_user(member.id)

                user["voice_time"] += seconds

                xp = int((seconds / 60) * VOICE_XP_PER_MINUTE)

                levels = self.bot.get_cog("Levels")

                if levels and xp > 0:
                    await levels.add_xp(member, xp)

                achievements = self.bot.get_cog("Achievements")

                if achievements:
                    await achievements.check_achievements(member)

        # ======================================================
        # USER JOINED VOICE
        # ======================================================

        elif after_channel and not before_channel:

            self.voice_times[member.id] = time.time()

        # ======================================================
        # USER SWITCHED CHANNEL
        # ======================================================

        elif before_channel != after_channel:

            if member.id in self.voice_times:

                joined = self.voice_times.pop(member.id)

                seconds = int(time.time() - joined)

                user = db.get_user(member.id)

                user["voice_time"] += seconds

                xp = int((seconds / 60) * VOICE_XP_PER_MINUTE)

                levels = self.bot.get_cog("Levels")

                if levels and xp > 0:
                    await levels.add_xp(member, xp)

            self.voice_times[member.id] = time.time()

    # ==========================================================
    # CLEANUP
    # ==========================================================

    def cog_unload(self):
        """Stop autosave when cog unloads."""
        self.save_loop.stop()


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):
    await bot.add_cog(Tracking(bot))
