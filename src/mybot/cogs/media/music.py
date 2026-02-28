import asyncio
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands

try:
    from mybot.utils.i18n import translate, translate_for_ctx, translate_for_interaction
except Exception:  # pragma: no cover
    from src.mybot.utils.i18n import translate, translate_for_ctx, translate_for_interaction

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None


YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
}

FFMPEG_OPTIONS = (
    "-reconnect",
    "1",
    "-reconnect_streamed",
    "1",
    "-reconnect_delay_max",
    "5",
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

    async def cog_load(self):
        # called when cog is loaded
        return

    @staticmethod
    def _t(ctx, key: str, default: str, **fmt) -> str:
        return translate_for_ctx(ctx, key, default=default, **fmt)

    # --- Spotify helpers ---
    async def _get_spotify_token(self) -> Optional[str]:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            return None

        if self._spotify_token and time.time() + 30 < self._spotify_token_expires_at:
            return self._spotify_token

        data = {"grant_type": "client_credentials"}
        auth = aiohttp.BasicAuth(client_id, client_secret)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://accounts.spotify.com/api/token", data=data, auth=auth
            ) as resp:
                if resp.status != 200:
                    return None
                j = await resp.json()
        token = j.get("access_token")
        expires_in = j.get("expires_in", 3600)
        self._spotify_token = token
        self._spotify_token_expires_at = time.time() + int(expires_in)
        return token

    async def _fetch_spotify_tracks(self, url: str, limit: int = 50) -> List[str]:
        """
        Return a list of search queries derived from a Spotify track or
        playlist URL.
        """
        token = await self._get_spotify_token()
        if not token:
            raise RuntimeError(
                "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not configured"
            )

        headers = {"Authorization": f"Bearer {token}"}
        # detect track or playlist id (support both URL and URI forms and
        # optional locale segments)
        TRACK_RE = r"open\.spotify\.com(?:/[^/]+)?/track/([A-Za-z0-9_-]+)"
        PLAYLIST_RE = r"open\.spotify\.com(?:/[^/]+)?/playlist/([A-Za-z0-9_-]+)"
        m_track = re.search(TRACK_RE, url)
        m_playlist = re.search(PLAYLIST_RE, url)
        if not m_track:
            m_track = re.search(r"spotify:track:([A-Za-z0-9_-]+)", url)
        if not m_playlist:
            m_playlist = re.search(r"spotify:playlist:([A-Za-z0-9_-]+)", url)
        queries: List[str] = []

        async with aiohttp.ClientSession() as session:
            if m_track:
                track_id = m_track.group(1)
                api = f"https://api.spotify.com/v1/tracks/{track_id}"
                async with session.get(api, headers=headers) as resp:
                    if resp.status != 200:
                        # try oEmbed fallback for public Spotify pages
                        try:
                            safe_q = quote(url, safe="")
                            oembed_url = "https://open.spotify.com/oembed?url=" + safe_q
                            async with session.get(oembed_url) as oresp:
                                if oresp.status == 200:
                                    oj = await oresp.json()
                                    title = oj.get("title")
                                    if title:
                                        queries.append(title)
                                        return queries
                        except Exception:
                            pass
                        text = await resp.text()
                        raise RuntimeError(f"Spotify API error {resp.status}: {text}")
                    j = await resp.json()
                name = j.get("name")
                artists = ", ".join([a["name"] for a in j.get("artists", [])])
                queries.append(f"{name} {artists}")
                return queries

            if m_playlist:
                playlist_id = m_playlist.group(1)
                api = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
                offset = 0
                while True:
                    params = {"limit": min(100, limit - len(queries)), "offset": offset}
                    async with session.get(api, headers=headers, params=params) as resp:
                        if resp.status != 200:
                            # try oEmbed fallback for playlist page
                            try:
                                safe_q = quote(url, safe="")
                                oembed_url = (
                                    f"https://open.spotify.com/oembed?url={safe_q}"
                                )
                                async with session.get(oembed_url) as oresp:
                                    if oresp.status == 200:
                                        oj = await oresp.json()
                                        title = oj.get("title")
                                        if title:
                                            queries.append(title)
                                            return queries
                            except Exception:
                                pass
                            text = await resp.text()
                            raise RuntimeError(
                                f"Spotify API error {resp.status}: {text}"
                            )
                        j = await resp.json()
                    items = j.get("items", [])
                    for it in items:
                        t = it.get("track") or {}
                        name = t.get("name")
                        artists = ", ".join([a["name"] for a in t.get("artists", [])])
                        if name:
                            queries.append(f"{name} {artists}")
                        if len(queries) >= limit:
                            break
                    if len(queries) >= limit:
                        break
                    if not j.get("next"):
                        break
                    offset += len(items)
                return queries

        # If we reached here, spotify api didn't match (or returned no items).
        # Try a lightweight page-title fallback for public Spotify links.
        title = await self._fetch_spotify_title(url)
        if title:
            return [title]

        return queries

    # --- existing helpers ---
    async def _fetch_spotify_title(self, url: str) -> Optional[str]:
        # fallback: fetch page title like "Song — Artist | Spotify"
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, timeout=10) as resp:
                    text = await resp.text()
            m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
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
        # already connected
        if ctx.voice_client and ctx.voice_client.is_connected():
            return ctx.voice_client

        # ensure author is in a voice channel
        author_vc = getattr(ctx.author, "voice", None)
        if not author_vc or not author_vc.channel:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.not_in_voice",
                    "You are not connected to a voice channel.",
                )
            )
            return None

        channel = author_vc.channel

        # check bot permissions in that channel
        me = ctx.guild.me if ctx.guild else None
        if me is None:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.bot_identity",
                    "Unable to determine bot member in this guild.",
                )
            )
            return None

        perms = channel.permissions_for(me)
        if not perms.connect:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.connect_permission",
                    "I don't have permission to connect to your voice channel (Connect permission missing).",
                )
            )
            return None
        if not perms.speak:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.speak_permission",
                    "I don't have permission to speak in your voice channel (Speak permission missing).",
                )
            )
            return None

        # Stage channels require special handling
        if getattr(channel, "stage_instance", None) is not None:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.stage_unsupported",
                    "Stage channels are not supported by this bot.",
                )
            )
            return None

        # attempt to connect
        try:
            vc = await channel.connect()
            return vc
        except Exception as e:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.join_failed",
                    "Failed to join voice channel: {error}",
                    error=str(e),
                )
            )
            return None

    async def _play_next(self, guild_id: int):
        async with self.players_lock:
            queue = self.queues.get(guild_id, [])
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            if not queue:
                vc = guild.voice_client
                if vc and vc.is_connected():
                    await vc.disconnect()
                self.now_playing[guild_id] = None
                return

            track = queue.pop(0)
            self.now_playing[guild_id] = track

            vc = guild.voice_client
            if not vc or not vc.is_connected():
                return

            def after(err):
                coro = self._play_next(guild_id)
                fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    fut.result()
                except Exception:
                    pass

            source = discord.FFmpegPCMAudio(
                track.source, **{"before_options": " ".join(FFMPEG_OPTIONS)}
            )
            vc.play(source, after=after)

    # --- commands ---
    @commands.hybrid_command(name="join", description="Join your voice channel")
    async def join(self, ctx: commands.Context):
        vc = await self._ensure_voice(ctx)
        if vc:
            await ctx.send(
                self._t(
                    ctx,
                    "music.msg.connected",
                    "Connected to {channel}",
                    channel=vc.channel.mention,
                )
            )

    @commands.hybrid_command(
        name="leave", description="Leave voice channel and clear queue"
    )
    async def leave(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        self.queues.pop(guild_id, None)
        self.now_playing[guild_id] = None
        await ctx.send(
            self._t(
                ctx,
                "music.msg.left",
                "Left the voice channel and cleared the queue.",
            )
        )

    @commands.hybrid_command(
        name="play", description="Play a YouTube URL or search term"
    )
    async def play(self, ctx: commands.Context, *, query: str):
        if YoutubeDL is None:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.ytdlp_missing",
                    "Playback requires `yt-dlp`. Install with `pip install yt-dlp`.",
                )
            )
            return

        guild_id = ctx.guild.id
        vc = await self._ensure_voice(ctx)
        if not vc:
            return

        original_query = query.strip()
        if not (
            original_query.startswith("http://")
            or original_query.startswith("https://")
        ):
            query = f"ytsearch:{original_query}"
        else:
            query = original_query

        # defer only for interactions; for prefix commands use typing indicator
        try:
            if isinstance(ctx, discord.Interaction):
                await ctx.response.defer()
            else:
                await ctx.trigger_typing()
        except Exception:
            pass
        try:
            info = await self._resolve_query(query)
        except Exception as e:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.resolve_source",
                    "Error resolving source: {error}",
                    error=str(e),
                )
            )
            return

        if "entries" in info:
            info = info["entries"][0]

        url = info.get("url") or info.get("webpage_url")
        if not url:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.no_url",
                    "Could not resolve a playable URL for that query.",
                )
            )
            return

        stream_url = info.get("url") or info.get("webpage_url")
        track = Track(
            title=info.get("title", "Unknown"),
            source=stream_url,
            requester=ctx.author,
            duration=info.get("duration"),
        )

        self.queues.setdefault(guild_id, []).append(track)
        await ctx.send(
            self._t(
                ctx,
                "music.msg.queued",
                "Queued: **{title}** (requested by {requester})",
                title=track.title,
                requester=ctx.author.display_name,
            )
        )

        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await self._play_next(guild_id)

    @commands.hybrid_command(
        name="spotify", description="Import Spotify track or playlist into the queue"
    )
    async def spotify(
        self, ctx: commands.Context, url: str, max_tracks: Optional[str] = None
    ):
        """Import a Spotify track or playlist into the queue (uses Spotify Web API).

        Requires environment variables `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
        """
        # normalize max_tracks: accept ints or strings like "[20]" and clamp to [1,200]
        try:
            if max_tracks is None:
                max_t = 25
            else:
                # already an int-like string or numeric
                if isinstance(max_tracks, int):
                    max_t = max_tracks
                else:
                    m = re.search(r"(\d+)", str(max_tracks))
                    if m:
                        max_t = int(m.group(1))
                    else:
                        try:
                            max_t = int(max_tracks)
                        except Exception:
                            max_t = 25
            # clamp limits
            max_t = max(1, min(200, int(max_t)))

            queries = await self._fetch_spotify_tracks(url, limit=max_t)
        except Exception as e:
            # If Spotify API forbids access (403) or similar, try a fallback
            msg = str(e)
            if (
                "403" in msg
                or "forbidden" in msg.lower()
                or "spotify api error" in msg.lower()
            ):
                title = await self._fetch_spotify_title(url)
                if title:
                    queries = [title]
                else:
                    await ctx.send(
                        self._t(
                            ctx,
                            "music.error.spotify",
                            "Spotify error: {error}",
                            error=str(e),
                        )
                    )
                    return
            else:
                await ctx.send(
                    self._t(
                        ctx,
                        "music.error.spotify",
                        "Spotify error: {error}",
                        error=str(e),
                    )
                )
                return

        if not queries:
            await ctx.send(
                self._t(
                    ctx,
                    "music.error.spotify_empty",
                    "No tracks found or failed to fetch from Spotify.",
                )
            )
            return

        await ctx.defer()
        guild_id = ctx.guild.id
        vc = await self._ensure_voice(ctx)
        if not vc:
            return

        # send initial status embed and update it periodically
        total = len(queries)
        embed = discord.Embed(
            title=self._t(ctx, "music.spotify.title", "Spotify Import"),
            description=self._t(
                ctx,
                "music.spotify.desc_progress",
                "Importing {total} tracks... 0/{total} added",
                total=total,
            ),
            color=0x1DB954,
        )
        # create cancel event and view so user can abort
        cancel_event = asyncio.Event()
        self._import_cancel_events[guild_id] = cancel_event
        view = ImportCancelView(cancel_event, ctx.author.id, getattr(ctx.guild, "id", None))
        status = await ctx.send(embed=embed, view=view)

        added = 0
        skipped = 0
        for idx, q in enumerate(queries, start=1):
            try:
                info = await self._resolve_query(f"ytsearch:{q}")
                if "entries" in info:
                    info = info["entries"][0]
                stream_url = info.get("url") or info.get("webpage_url")
                title = info.get("title", q)
                track = Track(
                    title=title,
                    source=stream_url,
                    requester=ctx.author,
                    duration=info.get("duration"),
                )
                self.queues.setdefault(guild_id, []).append(track)
                added += 1
            except Exception:
                skipped += 1

            # check cancellation
            if cancel_event.is_set():
                try:
                    embed.description = self._t(
                        ctx,
                        "music.spotify.desc_cancelled",
                        "Import canceled: {added} added, {skipped} skipped.",
                        added=added,
                        skipped=skipped,
                    )
                    for item in view.children:
                        item.disabled = True
                    await status.edit(embed=embed, view=view)
                except Exception:
                    pass
                break

            # update status every 5 items or on the last item
            if idx % 5 == 0 or idx == total:
                try:
                    embed.description = self._t(
                        ctx,
                        "music.spotify.desc_progress_dynamic",
                        "Importing {total} tracks... {added}/{total} added (skipped {skipped})",
                        total=total,
                        added=added,
                        skipped=skipped,
                    )
                    await status.edit(embed=embed, view=view)
                except Exception:
                    pass

        try:
            embed.description = self._t(
                ctx,
                "music.spotify.desc_complete",
                "Import complete: {added} added, {skipped} skipped.",
                added=added,
                skipped=skipped,
            )
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
            await ctx.send(self._t(ctx, "music.error.not_connected", "Not connected."))
            return
        if vc.is_playing():
            vc.stop()
            await ctx.send(self._t(ctx, "music.msg.skipped", "Skipped."))
        else:
            await ctx.send(self._t(ctx, "music.msg.nothing_playing", "Nothing is playing."))

    @commands.hybrid_command(name="queue", description="Show the queue")
    async def queue_cmd(self, ctx: commands.Context):
        q = self.queues.get(ctx.guild.id, [])
        if not q:
            await ctx.send(self._t(ctx, "music.msg.queue_empty", "Queue is empty."))
            return
        now_playing_obj = self.now_playing.get(ctx.guild.id)
        if now_playing_obj and now_playing_obj.title:
            now_title = now_playing_obj.title
        else:
            now_title = "Nothing"
        lines = [
            self._t(
                ctx,
                "music.msg.queue_now",
                "Now: **{title}**",
                title=now_title,
            )
        ]
        for i, t in enumerate(q[:10], start=1):
            lines.append(
                self._t(
                    ctx,
                    "music.msg.queue_entry",
                    "{index}. {title} — requested by {requester}",
                    index=i,
                    title=t.title,
                    requester=t.requester.display_name,
                )
            )
        await ctx.send("\n".join(lines))

    @commands.hybrid_command(name="now", description="Show now playing")
    async def now(self, ctx: commands.Context):
        now = self.now_playing.get(ctx.guild.id)
        if not now:
            await ctx.send(self._t(ctx, "music.msg.nothing_playing", "Nothing is playing."))
            return
        await ctx.send(
            self._t(
                ctx,
                "music.msg.now_playing",
                "Now playing: **{title}** — requested by {requester}",
                title=now.title,
                requester=now.requester.display_name,
            )
        )

    @commands.hybrid_command(name="stop", description="Stop and clear the queue")
    async def stop(self, ctx: commands.Context):
        vc = ctx.voice_client
        guild_id = ctx.guild.id
        if vc and vc.is_connected():
            vc.stop()
            await vc.disconnect()
        self.queues[guild_id] = []
        self.now_playing[guild_id] = None
        await ctx.send(
            self._t(
                ctx,
                "music.msg.stopped",
                "Stopped and cleared the queue.",
            )
        )


class ImportCancelView(discord.ui.View):
    def __init__(self, event: asyncio.Event, owner_id: int, guild_id: Optional[int]):
        super().__init__(timeout=None)
        self._event = event
        self._owner_id = owner_id
        self._guild_id = guild_id
        for child in self.children:
            try:
                child.label = translate(
                    "music.spotify.button_cancel",
                    guild_id=guild_id,
                    default="Cancel",
                )
            except Exception:
                pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # allow the requester or server admins
        # (administrator / manage_guild / manage_messages)
        if interaction.user.id != self._owner_id:
            perms = None
            if interaction.guild and hasattr(interaction.user, "guild_permissions"):
                perms = interaction.user.guild_permissions
            if not (
                perms
                and (perms.administrator or perms.manage_guild or perms.manage_messages)
            ):
                await interaction.response.send_message(
                    translate_for_interaction(
                        interaction,
                        "music.spotify.error_cancel_perms",
                        default="Only the requester or an admin can cancel the import.",
                    ),
                    ephemeral=True,
                )
                return
        self._event.set()
        for item in self.children:
            item.disabled = True
        try:
            await interaction.response.edit_message(
                content=translate_for_interaction(
                    interaction,
                    "music.spotify.msg_cancelled",
                    default="Import canceled.",
                ),
                view=self,
            )
        except Exception:
            pass

    # Note: other helpers and command methods belong to the `Music` cog and
    # were intentionally implemented as methods of `Music` so they can access
    # cog state (`self.queues`, `self.now_playing`, etc.).


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
