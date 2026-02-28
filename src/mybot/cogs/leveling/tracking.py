import time

from discord.ext import commands, tasks

from .utils.level_config import (get_message_cooldown, get_voice_xp_per_minute,
                                 get_xp_per_message)


class Tracking(commands.Cog):
    """Tracks messages, voice time, and XP."""

    def __init__(self, bot):
        self.bot = bot

        # cooldowns for message xp: (user_id, guild_id) -> timestamp
        self.cooldowns = {}

        # voice join timestamps: (user_id, guild_id) -> timestamp
        self.voice_times = {}

        # start loops
        self.save_loop.start()
        self.voice_loop.start()  # FIX: new loop

    # ==========================================================
    # AUTO SAVE
    # ==========================================================

    @tasks.loop(minutes=1)
    async def save_loop(self):
        """Periodically save database for all guilds."""
        for guild in self.bot.guilds:
            self.bot.db.save(guild_id=guild.id)

    # ==========================================================
    # VOICE UPDATE LOOP (FIX)
    # ==========================================================

    @tasks.loop(minutes=1)
    async def voice_loop(self):
        """Update voice time every minute."""

        now = time.time()

        for (user_id, guild_id) in list(self.voice_times.keys()):

            joined = self.voice_times[(user_id, guild_id)]

            seconds = int(now - joined)

            if seconds <= 0:
                continue

            user = self.bot.db.get_user(user_id, guild_id=guild_id)

            user["voice_time"] += seconds

            xp = int((seconds / 60) * get_voice_xp_per_minute(guild_id=guild_id))

            levels = self.bot.get_cog("Levels")

            if levels and xp > 0:

                guild = self.bot.get_guild(guild_id)
                member = guild.get_member(user_id) if guild else None

                if member:
                    await levels.add_xp(member, xp)

            # reset timer
            self.voice_times[(user_id, guild_id)] = now

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

                        self.voice_times[(member.id, guild.id)] = now

        print("[TRACKING] Voice timers restored")

    # ==========================================================
    # MESSAGE TRACKING
    # ==========================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        guild_id = getattr(getattr(message, 'guild', None), 'id', None)
        if guild_id is None:
            return

        user_id = message.author.id
        now = time.time()

        cooldown_key = (user_id, guild_id)
        if cooldown_key in self.cooldowns:

            elapsed = now - self.cooldowns[cooldown_key]

            if elapsed < get_message_cooldown(guild_id=guild_id):
                return

        self.cooldowns[cooldown_key] = now

        db = self.bot.db
        user = db.get_user(user_id, guild_id=guild_id)

        user["messages"] += 1

        levels = self.bot.get_cog("Levels")

        if levels:
            await levels.add_xp(message.author, get_xp_per_message(guild_id=guild_id))

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
        guild_id = member.guild.id

        before_channel = before.channel
        after_channel = after.channel

        voice_key = (member.id, guild_id)

        # LEFT VOICE
        if before_channel and not after_channel:

            if voice_key in self.voice_times:

                joined = self.voice_times.pop(voice_key)

                seconds = int(time.time() - joined)

                if seconds > 0:

                    user = db.get_user(member.id, guild_id=guild_id)

                    user["voice_time"] += seconds

        # JOINED VOICE
        elif after_channel and not before_channel:

            self.voice_times[voice_key] = time.time()

        # SWITCHED CHANNEL
        elif before_channel != after_channel:

            if voice_key in self.voice_times:

                joined = self.voice_times.pop(voice_key)

                seconds = int(time.time() - joined)

                if seconds > 0:

                    user = db.get_user(member.id, guild_id=guild_id)

                    user["voice_time"] += seconds

            self.voice_times[voice_key] = time.time()

    # ==========================================================

    def cog_unload(self):

        self.save_loop.stop()
        self.voice_loop.stop()


# ==========================================================


async def setup(bot):

    await bot.add_cog(Tracking(bot))
