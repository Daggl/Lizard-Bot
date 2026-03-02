"""Lizard Cog — plays the lizard sound in voice."""

import asyncio
import os

import discord
from discord.ext import commands

# Resolve the sound file relative to the repo root
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
LIZARD_SOUND = os.path.join(_REPO_ROOT, "assets", "sounds", "lizard.mp3")


class Lizard(commands.Cog, name="lizard"):
    """Plays the legendary lizard sound in your voice channel."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _ensure_voice(self, ctx: commands.Context):
        """Join the author's voice channel, return VoiceClient or None."""
        if ctx.voice_client and ctx.voice_client.is_connected():
            return ctx.voice_client

        author_vc = getattr(ctx.author, "voice", None)
        if not author_vc or not author_vc.channel:
            await ctx.send("Du bist in keinem Voice-Channel!")
            return None

        channel = author_vc.channel
        me = ctx.guild.me if ctx.guild else None
        if me is None:
            return None

        perms = channel.permissions_for(me)
        if not perms.connect or not perms.speak:
            await ctx.send("Mir fehlen die Berechtigungen für deinen Voice-Channel.")
            return None

        try:
            return await channel.connect()
        except Exception as e:
            await ctx.send(f"Konnte dem Channel nicht beitreten: {e}")
            return None

    @commands.hybrid_command(name="lizard", description="🦎 Plays the lizard sound")
    async def lizard(self, ctx: commands.Context):
        if not os.path.isfile(LIZARD_SOUND):
            await ctx.send("Sound-Datei nicht gefunden!")
            return

        vc = await self._ensure_voice(ctx)
        if vc is None:
            return

        # Stop anything currently playing
        if vc.is_playing():
            vc.stop()

        loop = self.bot.loop

        done = asyncio.Event()

        def after(error):
            async def _cleanup():
                try:
                    if vc.is_connected():
                        await vc.disconnect()
                except Exception:
                    pass
                done.set()

            asyncio.run_coroutine_threadsafe(_cleanup(), loop)

        source = discord.FFmpegPCMAudio(LIZARD_SOUND)
        vc.play(source, after=after)
        await ctx.send("🦎")

        # Wait for playback to finish, then the after callback disconnects
        try:
            await asyncio.wait_for(done.wait(), timeout=60)
        except asyncio.TimeoutError:
            if vc.is_connected():
                await vc.disconnect()


async def setup(bot: commands.Bot):
    await bot.add_cog(Lizard(bot))
