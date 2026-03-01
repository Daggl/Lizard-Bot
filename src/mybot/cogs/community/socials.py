"""Social Media cog — monitors Twitch, YouTube, Twitter/X and custom feeds.

Posts live/stream/upload notifications to per-activity configured channels.
All settings are per-guild and stored in social_media.json.
"""

import asyncio
import traceback
from datetime import datetime, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from mybot.utils.config import load_cog_config
from mybot.utils.i18n import translate
from mybot.utils.jsonstore import safe_load_json, safe_save_json
from mybot.utils.paths import guild_data_path

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _cfg(guild_id: int | str | None = None) -> dict:
    try:
        return load_cog_config("social_media", guild_id=guild_id) or {}
    except Exception:
        return {}


def _source_cfg(guild_id: int | str | None, source: str) -> dict:
    """Return config dict for a specific source (twitch, youtube, twitter, custom)."""
    cfg = _cfg(guild_id)
    return cfg.get(source.upper(), {}) if isinstance(cfg.get(source.upper()), dict) else {}


# ---------------------------------------------------------------------------
# State tracking (already posted)
# ---------------------------------------------------------------------------

def _load_posted(guild_id: int | str | None) -> dict:
    path = guild_data_path(guild_id, "social_media_data.json")
    if not path:
        return {"twitch": [], "youtube": [], "twitter": [], "custom": []}
    data = safe_load_json(path, default={"twitch": [], "youtube": [], "twitter": [], "custom": []})
    return data


def _save_posted(guild_id: int | str | None, data: dict):
    path = guild_data_path(guild_id, "social_media_data.json")
    if path:
        # Keep only last 100 entries per source
        for key in ("twitch", "youtube", "twitter", "custom"):
            if key in data and isinstance(data[key], list):
                data[key] = data[key][-100:]
        safe_save_json(path, data)


# ---------------------------------------------------------------------------
# Twitch API (uses Helix — requires Client-ID + OAuth token)
# ---------------------------------------------------------------------------

async def _fetch_twitch_streams(usernames: list[str], client_id: str, oauth_token: str) -> list[dict]:
    """Check if given Twitch usernames are currently live."""
    if not usernames or not client_id or not oauth_token:
        return []
    items = []
    try:
        params = "&".join(f"user_login={u.strip().lower()}" for u in usernames[:100])
        url = f"https://api.twitch.tv/helix/streams?{params}"
        headers = {
            "Client-ID": client_id,
            "Authorization": f"Bearer {oauth_token}",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        for stream in data.get("data", []):
            items.append({
                "source": "twitch",
                "id": f"twitch:{stream.get('id', '')}",
                "username": stream.get("user_name", ""),
                "title": stream.get("title", ""),
                "game": stream.get("game_name", ""),
                "url": f"https://twitch.tv/{stream.get('user_login', '')}",
                "thumbnail": (stream.get("thumbnail_url", "")
                              .replace("{width}", "440")
                              .replace("{height}", "248")),
                "viewers": stream.get("viewer_count", 0),
            })
    except Exception:
        traceback.print_exc()
    return items


# ---------------------------------------------------------------------------
# YouTube RSS (no API key needed — public RSS feed)
# ---------------------------------------------------------------------------

async def _fetch_youtube_latest(channel_ids: list[str]) -> list[dict]:
    """Fetch latest videos from YouTube channels via RSS."""
    items = []
    try:
        async with aiohttp.ClientSession() as session:
            for cid in channel_ids[:20]:
                cid = cid.strip()
                if not cid:
                    continue
                url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status != 200:
                            continue
                        text = await resp.text()
                    # Simple XML parsing without extra dependencies
                    entries = text.split("<entry>")[1:]  # skip header
                    for entry in entries[:3]:  # only latest 3 per channel
                        video_id = _xml_tag(entry, "yt:videoId")
                        title = _xml_tag(entry, "title")
                        author = _xml_tag(entry, "name")
                        published = _xml_tag(entry, "published")
                        if video_id:
                            items.append({
                                "source": "youtube",
                                "id": f"youtube:{video_id}",
                                "title": title or "New Video",
                                "author": author or "",
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                                "published": published or "",
                            })
                except Exception:
                    continue
    except Exception:
        traceback.print_exc()
    return items


def _xml_tag(text: str, tag: str) -> str:
    """Extract text content from a simple XML tag (no attributes)."""
    start = text.find(f"<{tag}>")
    if start == -1:
        start = text.find(f"<{tag} ")
        if start == -1:
            return ""
        # find the > after attributes
        start = text.find(">", start)
        if start == -1:
            return ""
        start += 1
    else:
        start += len(f"<{tag}>")
    end = text.find(f"</{tag}>", start)
    if end == -1:
        return ""
    return text[start:end].strip()


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class SocialMedia(commands.Cog):
    """Monitors social media and posts notifications to configured channels."""

    def __init__(self, bot):
        self.bot = bot
        self.check_socials.start()

    def cog_unload(self):
        self.check_socials.cancel()

    # ------------------------------------------------------------------
    # /socialcheck — manual trigger
    # ------------------------------------------------------------------

    @commands.hybrid_command(name="socialcheck", description="Manually check all social media feeds now.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def socialcheck_cmd(self, ctx: commands.Context):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        if guild_id is None:
            await ctx.send("❌ This command must be used in a server.")
            return

        await ctx.send(translate(
            "socials.msg.checking", guild_id=guild_id,
            default="🔍 Checking social media feeds...",
        ))
        count = await self._check_guild(ctx.guild)
        await ctx.send(translate(
            "socials.msg.check_done", guild_id=guild_id,
            default="✅ Check complete. {count} new notification(s) posted.",
            count=count,
        ))

    # ------------------------------------------------------------------
    # /socialsources — show configured sources
    # ------------------------------------------------------------------

    @commands.hybrid_command(name="socialsources", description="Show configured social media sources.")
    async def socialsources(self, ctx: commands.Context):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        cfg = _cfg(guild_id)

        lines = []
        for source_name in ("TWITCH", "YOUTUBE", "TWITTER", "CUSTOM"):
            src = cfg.get(source_name, {})
            if not isinstance(src, dict):
                continue
            enabled = bool(src.get("ENABLED", False))
            channel_id = src.get("CHANNEL_ID", 0)
            icon = "✅" if enabled else "❌"
            lines.append(f"{icon} **{source_name.title()}** — Channel: <#{channel_id}>" if channel_id else f"{icon} **{source_name.title()}** — Not configured")

        if not lines:
            lines.append("No social media sources configured.")

        embed = discord.Embed(
            title=translate("socials.sources.title", guild_id=guild_id,
                            default="📡 Social Media Sources"),
            description="\n".join(lines),
            color=discord.Color.purple(),
        )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # Automated loop
    # ------------------------------------------------------------------

    @tasks.loop(minutes=5)
    async def check_socials(self):
        """Periodically check all guilds for social media updates."""
        for guild in self.bot.guilds:
            try:
                await self._check_guild(guild)
            except Exception as exc:
                print(f"[SocialMedia] Error checking guild {guild.id}: {exc}")
            await asyncio.sleep(2)

    @check_socials.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def _check_guild(self, guild: discord.Guild) -> int:
        """Check and post social updates for a single guild. Returns count of new items posted."""
        guild_id = guild.id
        cfg = _cfg(guild_id)
        posted_data = _load_posted(guild_id)
        total_new = 0

        # --- Twitch ---
        twitch_cfg = cfg.get("TWITCH", {})
        if isinstance(twitch_cfg, dict) and twitch_cfg.get("ENABLED"):
            ch_id = int(twitch_cfg.get("CHANNEL_ID", 0) or 0)
            usernames = [u.strip() for u in str(twitch_cfg.get("USERNAMES", "")).split(",") if u.strip()]
            client_id = str(twitch_cfg.get("CLIENT_ID", "") or "")
            oauth_token = str(twitch_cfg.get("OAUTH_TOKEN", "") or "")
            if ch_id and usernames and client_id and oauth_token:
                channel = self.bot.get_channel(ch_id) or guild.get_channel(ch_id)
                if channel:
                    streams = await _fetch_twitch_streams(usernames, client_id, oauth_token)
                    posted_set = set(posted_data.get("twitch", []))
                    for stream in streams:
                        sid = stream["id"]
                        if sid in posted_set:
                            continue
                        embed = discord.Embed(
                            title=f"🟣 {stream['username']} is LIVE!",
                            description=f"**{stream['title']}**\n\nPlaying: {stream['game']}\n👁 {stream['viewers']} viewers",
                            url=stream["url"],
                            color=discord.Color.purple(),
                            timestamp=datetime.now(timezone.utc),
                        )
                        if stream.get("thumbnail"):
                            embed.set_image(url=stream["thumbnail"])
                        try:
                            await channel.send(embed=embed)
                            posted_data.setdefault("twitch", []).append(sid)
                            total_new += 1
                        except Exception as exc:
                            print(f"[SocialMedia] Twitch post failed: {exc}")

        # --- YouTube ---
        youtube_cfg = cfg.get("YOUTUBE", {})
        if isinstance(youtube_cfg, dict) and youtube_cfg.get("ENABLED"):
            ch_id = int(youtube_cfg.get("CHANNEL_ID", 0) or 0)
            yt_channel_ids = [c.strip() for c in str(youtube_cfg.get("YOUTUBE_CHANNEL_IDS", "")).split(",") if c.strip()]
            if ch_id and yt_channel_ids:
                channel = self.bot.get_channel(ch_id) or guild.get_channel(ch_id)
                if channel:
                    videos = await _fetch_youtube_latest(yt_channel_ids)
                    posted_set = set(posted_data.get("youtube", []))
                    for video in videos:
                        vid = video["id"]
                        if vid in posted_set:
                            continue
                        embed = discord.Embed(
                            title=f"🔴 {video['author']} uploaded a new video!",
                            description=f"**{video['title']}**",
                            url=video["url"],
                            color=discord.Color.red(),
                            timestamp=datetime.now(timezone.utc),
                        )
                        if video.get("thumbnail"):
                            embed.set_image(url=video["thumbnail"])
                        try:
                            await channel.send(embed=embed)
                            posted_data.setdefault("youtube", []).append(vid)
                            total_new += 1
                        except Exception as exc:
                            print(f"[SocialMedia] YouTube post failed: {exc}")

        # --- Twitter/X ---
        twitter_cfg = cfg.get("TWITTER", {})
        if isinstance(twitter_cfg, dict) and twitter_cfg.get("ENABLED"):
            # Twitter/X API requires Bearer token; placeholder for future implementation
            pass

        # --- Custom webhooks/feeds ---
        custom_cfg = cfg.get("CUSTOM", {})
        if isinstance(custom_cfg, dict) and custom_cfg.get("ENABLED"):
            # Custom source placeholder for user-defined RSS/webhook feeds
            pass

        if total_new:
            _save_posted(guild_id, posted_data)

        return total_new


async def setup(bot):
    await bot.add_cog(SocialMedia(bot))
