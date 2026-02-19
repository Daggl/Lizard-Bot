import asyncio
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiohttp
import discord
from discord.ext import commands

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None


YTDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
}

FFMPEG_OPTIONS = (
    '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5'
)


@dataclass
class Track:
    title: str
    source: str
    requester: discord.Member
    duration: Optional[int] = None


class Music(commands.Cog, name="music"):
    """Music Cog with queueing, YouTube playback and Spotify API integration.

    Spotify integration uses Client Credentials flow to fetch playlist/track metadata
    and then searches YouTube for matching streams.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues: Dict[int, List[Track]] = {}
        self.now_playing: Dict[int, Optional[Track]] = {}
        self.players_lock = asyncio.Lock()
        self._spotify_token: Optional[str] = None
        self._spotify_token_expires_at: float = 0.0
        # map guild_id -> asyncio.Event used to cancel ongoing imports
        self._import_cancel_events: Dict[int, asyncio.Event] = {}

    # --- Spotify helpers ---
    async def _get_spotify_token(self) -> Optional[str]:
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        if not client_id or not client_secret:
            return None

        if self._spotify_token and time.time() + 30 < self._spotify_token_expires_at:
            return self._spotify_token

        data = {'grant_type': 'client_credentials'}
        auth = aiohttp.BasicAuth(client_id, client_secret)
        async with aiohttp.ClientSession() as session:
            async with session.post('https://accounts.spotify.com/api/token', data=data, auth=auth) as resp:
                if resp.status != 200:
                    return None
                j = await resp.json()
        token = j.get('access_token')
        expires_in = j.get('expires_in', 3600)
        self._spotify_token = token
        self._spotify_token_expires_at = time.time() + int(expires_in)
        return token

    async def _fetch_spotify_tracks(self, url: str, limit: int = 50) -> List[str]:
        """Return a list of search queries derived from a Spotify track or playlist URL."""
        token = await self._get_spotify_token()
        if not token:
            raise RuntimeError('SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not configured')

        headers = {'Authorization': f'Bearer {token}'}
        # detect track or playlist id
        m_track = re.search(r'open.spotify.com/track/([A-Za-z0-9_-]+)', url)
        m_playlist = re.search(r'open.spotify.com/playlist/([A-Za-z0-9_-]+)', url)
        queries: List[str] = []

        async with aiohttp.ClientSession() as session:
            if m_track:
                track_id = m_track.group(1)
                api = f'https://api.spotify.com/v1/tracks/{track_id}'
                async with session.get(api, headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    j = await resp.json()
                name = j.get('name')
                artists = ', '.join([a['name'] for a in j.get('artists', [])])
                queries.append(f"{name} {artists}")
                return queries

            if m_playlist:
                playlist_id = m_playlist.group(1)
                api = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
                offset = 0
                while True:
                    params = {'limit': min(100, limit - len(queries)), 'offset': offset}
                    async with session.get(api, headers=headers, params=params) as resp:
                        if resp.status != 200:
                            break
                        j = await resp.json()
                    items = j.get('items', [])
                    for it in items:
                        t = it.get('track') or {}
                        name = t.get('name')
                        artists = ', '.join([a['name'] for a in t.get('artists', [])])
                        if name:
                            queries.append(f"{name} {artists}")
                        if len(queries) >= limit:
                            break
                    if len(queries) >= limit:
                        break
                    if not j.get('next'):
                        break
                    offset += len(items)
                return queries

        return queries


class ImportCancelView(discord.ui.View):
    def __init__(self, event: asyncio.Event, owner_id: int):
        super().__init__(timeout=None)
        self._event = event
        self._owner_id = owner_id

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # allow the requester or server admins (administrator / manage_guild / manage_messages)
        if interaction.user.id != self._owner_id:
            perms = None
            if interaction.guild and hasattr(interaction.user, 'guild_permissions'):
                perms = interaction.user.guild_permissions
            if not (perms and (perms.administrator or perms.manage_guild or perms.manage_messages)):
                await interaction.response.send_message("Only the requester or an admin can cancel the import.", ephemeral=True)
                return
        self._event.set()
        for item in self.children:
            item.disabled = True
        try:
            await interaction.response.edit_message(content="Import abgebrochen.", view=self)
        except Exception:
            pass

    # --- existing helpers ---
    async def _fetch_spotify_title(self, url: str) -> Optional[str]:
        # fallback: fetch page title like "Song — Artist | Spotify"
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, timeout=10) as resp:
                    text = await resp.text()
            m = re.search(r'<title>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
            if m:
                title = m.group(1).strip()
                title = re.sub(r"\s+\|\s*Spotify$", "", title)
                return title
        except Exception:
            return None
        return None

    async def _resolve_query(self, query: str) -> Dict:
        if YoutubeDL is None:
            raise RuntimeError("yt-dlp not installed. Please `pip install yt-dlp`.")

        def run():
            with YoutubeDL(YTDL_OPTS) as ytdl:
                return ytdl.extract_info(query, download=False)

        return await asyncio.to_thread(run)

    async def _ensure_voice(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_connected():
            return ctx.voice_client
        if ctx.author.voice and ctx.author.voice.channel:
            return await ctx.author.voice.channel.connect()
        await ctx.send("You are not connected to a voice channel.")
        return None

    async def _play_next(self, guild_id: int):
        async with self.players_lock:
            queue = self.queues.get(guild_id, [])
            if not queue:
                vc = self.bot.get_guild(guild_id).voice_client
                if vc and vc.is_connected():
                    await vc.disconnect()
                self.now_playing[guild_id] = None
                return

            track = queue.pop(0)
            self.now_playing[guild_id] = track

            vc = self.bot.get_guild(guild_id).voice_client
            if not vc or not vc.is_connected():
                return

            def after(err):
                coro = self._play_next(guild_id)
                fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    fut.result()
                except Exception:
                    pass

            source = discord.FFmpegPCMAudio(track.source, **{'before_options': ' '.join(FFMPEG_OPTIONS)})
            vc.play(source, after=after)

    # --- commands ---
    @commands.hybrid_command(name="join", description="Join your voice channel")
    async def join(self, ctx: commands.Context):
        vc = await self._ensure_voice(ctx)
        if vc:
            await ctx.send(f"Connected to {vc.channel.mention}")

    @commands.hybrid_command(name="leave", description="Leave voice channel and clear queue")
    async def leave(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        self.queues.pop(guild_id, None)
        self.now_playing[guild_id] = None
        await ctx.send("Left the voice channel and cleared the queue.")

    @commands.hybrid_command(name="play", description="Play a YouTube URL or search term")
    async def play(self, ctx: commands.Context, *, query: str):
        if YoutubeDL is None:
            await ctx.send("Playback requires `yt-dlp`. Install with `pip install yt-dlp`.")
            return

        guild_id = ctx.guild.id
        vc = await self._ensure_voice(ctx)
        if not vc:
            return

        original_query = query.strip()
        if not (original_query.startswith('http://') or original_query.startswith('https://')):
            query = f"ytsearch:{original_query}"
        else:
            query = original_query

        await ctx.defer()
        try:
            info = await self._resolve_query(query)
        except Exception as e:
            await ctx.send(f"Error resolving source: {e}")
            return

        if 'entries' in info:
            info = info['entries'][0]

        url = info.get('url') or info.get('webpage_url')
        if not url:
            await ctx.send("Could not resolve a playable URL for that query.")
            return

        stream_url = info.get('url') or info.get('webpage_url')
        track = Track(title=info.get('title', 'Unknown'), source=stream_url, requester=ctx.author, duration=info.get('duration'))

        self.queues.setdefault(guild_id, []).append(track)
        await ctx.send(f"Queued: **{track.title}** (requested by {ctx.author.display_name})")

        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await self._play_next(guild_id)

    @commands.hybrid_command(name="spotify", description="Import Spotify track or playlist into the queue")
    async def spotify(self, ctx: commands.Context, url: str, max_tracks: int = 25):
        """Import a Spotify track or playlist into the queue (uses Spotify Web API).

        Requires environment variables `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
        """
        try:
            queries = await self._fetch_spotify_tracks(url, limit=max_tracks)
        except Exception as e:
            await ctx.send(f"Spotify error: {e}")
            return

        if not queries:
            await ctx.send("No tracks found or failed to fetch from Spotify.")
            return

        await ctx.defer()
        guild_id = ctx.guild.id
        vc = await self._ensure_voice(ctx)
        if not vc:
            return

        # send initial status embed and update it periodically
        total = len(queries)
        embed = discord.Embed(title="Spotify Import", description=f"Importing {total} tracks... 0/{total} added", color=0x1DB954)
        # create cancel event and view so user can abort
        cancel_event = asyncio.Event()
        self._import_cancel_events[guild_id] = cancel_event
        view = ImportCancelView(cancel_event, ctx.author.id)
        status = await ctx.send(embed=embed, view=view)

        added = 0
        skipped = 0
        for idx, q in enumerate(queries, start=1):
            try:
                info = await self._resolve_query(f"ytsearch:{q}")
                if 'entries' in info:
                    info = info['entries'][0]
                stream_url = info.get('url') or info.get('webpage_url')
                title = info.get('title', q)
                track = Track(title=title, source=stream_url, requester=ctx.author, duration=info.get('duration'))
                self.queues.setdefault(guild_id, []).append(track)
                added += 1
            except Exception:
                skipped += 1

            # check cancellation
            if cancel_event.is_set():
                try:
                    embed.description = f"Import abgebrochen: {added} added, {skipped} skipped."
                    for item in view.children:
                        item.disabled = True
                    await status.edit(embed=embed, view=view)
                except Exception:
                    pass
                break

            # update status every 5 items or on the last item
            if idx % 5 == 0 or idx == total:
                try:
                    embed.description = f"Importing {total} tracks... {added}/{total} added (skipped {skipped})"
                    await status.edit(embed=embed, view=view)
                except Exception:
                    pass

        try:
            embed.description = f"Import complete: {added} added, {skipped} skipped."
            for item in view.children:
                item.disabled = True
            await status.edit(embed=embed, view=view)
        except Exception:
            pass

        # cleanup cancel event
        try:
            del self._import_cancel_events[guild_id]
        except KeyError:
            pass

        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await self._play_next(guild_id)

    @commands.hybrid_command(name="skip", description="Skip current track")
    async def skip(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            await ctx.send("Not connected.")
            return
        if vc.is_playing():
            vc.stop()
            await ctx.send("Skipped.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.hybrid_command(name="queue", description="Show the queue")
    async def queue_cmd(self, ctx: commands.Context):
        q = self.queues.get(ctx.guild.id, [])
        if not q:
            await ctx.send("Queue is empty.")
            return
        lines = [f"Now: **{self.now_playing.get(ctx.guild.id).title if self.now_playing.get(ctx.guild.id) else 'Nothing'}**"]
        for i, t in enumerate(q[:10], start=1):
            lines.append(f"{i}. {t.title} — requested by {t.requester.display_name}")
        await ctx.send("\n".join(lines))

    @commands.hybrid_command(name="now", description="Show now playing")
    async def now(self, ctx: commands.Context):
        now = self.now_playing.get(ctx.guild.id)
        if not now:
            await ctx.send("Nothing is playing.")
            return
        await ctx.send(f"Now playing: **{now.title}** — requested by {now.requester.display_name}")

    @commands.hybrid_command(name="stop", description="Stop and clear the queue")
    async def stop(self, ctx: commands.Context):
        vc = ctx.voice_client
        guild_id = ctx.guild.id
        if vc and vc.is_connected():
            vc.stop()
            await vc.disconnect()
        self.queues[guild_id] = []
        self.now_playing[guild_id] = None
        await ctx.send("Stopped and cleared the queue.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
