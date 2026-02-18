import os
import discord
import wavelink

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


class Music(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot

    # ===============================
    # CONNECT LAVALINK
    # ===============================

    @commands.Cog.listener()
    async def on_ready(self):

        if wavelink.Pool.nodes:
            return

        node = wavelink.Node(
            uri="http://127.0.0.1:2333",
            password="youshallnotpass"
        )

        await wavelink.Pool.connect(
            nodes=[node],
            client=self.bot,
            spotify=wavelink.SpotifyClient(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET
            )
        )

        print("✅ Lavalink verbunden")

    # ===============================
    # PLAY
    # ===============================

    @commands.command()
    async def play(self, ctx: commands.Context, *, query: str):

        if not ctx.author.voice:

            return await ctx.send(
                "❌ Du musst in einem Voice Channel sein"
            )

        player: wavelink.Player = ctx.voice_client

        if not player:

            player = await ctx.author.voice.channel.connect(
                cls=wavelink.Player
            )

        # Spotify Support
        if "spotify.com" in query:

            tracks = await wavelink.Playable.search(
                query,
                source=wavelink.TrackSource.SPOTIFY
            )

        else:

            tracks = await wavelink.Playable.search(query)

        if not tracks:

            return await ctx.send("❌ Nichts gefunden")

        if isinstance(tracks, wavelink.Playlist):

            for track in tracks.tracks:

                await player.queue.put(track)

            await ctx.send(
                f"✅ Playlist hinzugefügt: {tracks.name}"
            )

        else:

            track = tracks[0]

            await player.queue.put(track)

            await ctx.send(
                f"🎵 Hinzugefügt: {track.title}"
            )

        if not player.playing:

            await player.play(
                player.queue.get(),
                volume=50
            )

    # ===============================
    # SKIP
    # ===============================

    @commands.command()
    async def skip(self, ctx):

        player: wavelink.Player = ctx.voice_client

        if not player:

            return

        await player.skip()

        await ctx.send("⏭️ Übersprungen")

    # ===============================
    # STOP
    # ===============================

    @commands.command()
    async def stop(self, ctx):

        player: wavelink.Player = ctx.voice_client

        if not player:

            return

        await player.disconnect()

        await ctx.send("⏹️ Gestoppt")

    # ===============================
    # NEXT TRACK AUTO PLAY
    # ===============================

    @commands.Cog.listener()
    async def on_wavelink_track_end(
        self,
        payload: wavelink.TrackEndEventPayload
    ):

        player = payload.player

        if player.queue:

            await player.play(
                player.queue.get(),
                volume=50
            )


# ===============================
# SETUP
# ===============================

async def setup(bot):

    await bot.add_cog(Music(bot))
