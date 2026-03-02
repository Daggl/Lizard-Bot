"""Social Media cog — monitors Twitch, YouTube, Twitter/X, TikTok and custom feeds.

Uses a per-channel + per-creator configuration model.  Each platform section
contains a ``CHANNELS`` list where every entry maps a Discord text channel to
one or more creators.  This makes it easy to send different creators to
different channels without the older route/map abstraction.

All settings are per-guild and stored in ``social_media.json``.
"""

import asyncio
import re as _re
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
# Supported platforms
# ---------------------------------------------------------------------------
PLATFORMS = ("TWITCH", "YOUTUBE", "TWITTER", "TIKTOK")
PLATFORM_CHOICES = [
    app_commands.Choice(name="Twitch", value="TWITCH"),
    app_commands.Choice(name="YouTube", value="YOUTUBE"),
    app_commands.Choice(name="Twitter / X", value="TWITTER"),
    app_commands.Choice(name="TikTok", value="TIKTOK"),
]

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _cfg(guild_id: int | str | None = None) -> dict:
    try:
        return load_cog_config("social_media", guild_id=guild_id) or {}
    except Exception:
        return {}


def _channels_list(platform_cfg: dict) -> list[dict]:
    """Return the CHANNELS list from a platform config (new schema)."""
    raw = platform_cfg.get("CHANNELS", [])
    if isinstance(raw, list):
        return [c for c in raw if isinstance(c, dict)]
    return []


def _all_creators(platform_cfg: dict) -> list[str]:
    """Collect every creator across all channel entries for a platform."""
    creators = []
    for entry in _channels_list(platform_cfg):
        for c in entry.get("CREATORS", []):
            c = str(c).strip()
            if c and c not in creators:
                creators.append(c)
    return creators


def _creator_to_channel_id(platform_cfg: dict) -> dict[str, int]:
    """Build a creator→channel_id lookup from the CHANNELS list."""
    mapping: dict[str, int] = {}
    for entry in _channels_list(platform_cfg):
        ch_id = int(entry.get("CHANNEL_ID", 0) or 0)
        if not ch_id:
            continue
        for c in entry.get("CREATORS", []):
            c = str(c).strip().lower()
            if c:
                mapping[c] = ch_id
    return mapping


# ---------------------------------------------------------------------------
# State tracking (already posted)
# ---------------------------------------------------------------------------

def _load_posted(guild_id: int | str | None) -> dict:
    path = guild_data_path(guild_id, "social_media_data.json")
    if not path:
        return {"twitch": [], "youtube": [], "twitter": [], "tiktok": [], "custom": []}
    data = safe_load_json(path, default={"twitch": [], "youtube": [], "twitter": [], "tiktok": [], "custom": []})
    return data


def _save_posted(guild_id: int | str | None, data: dict):
    path = guild_data_path(guild_id, "social_media_data.json")
    if path:
        for key in ("twitch", "youtube", "twitter", "tiktok", "custom"):
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
                    entries = text.split("<entry>")[1:]
                    for entry in entries[:3]:
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
# TikTok (public page scraping — no API key needed)
# ---------------------------------------------------------------------------

async def _fetch_tiktok_latest(usernames: list[str]) -> list[dict]:
    """Fetch latest TikTok video IDs by parsing the public profile page."""
    items = []
    try:
        async with aiohttp.ClientSession() as session:
            for username in usernames[:10]:
                username = username.strip().lstrip("@")
                if not username:
                    continue
                url = f"https://www.tiktok.com/@{username}"
                try:
                    headers = {
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=20),
                        allow_redirects=True,
                    ) as resp:
                        if resp.status != 200:
                            continue
                        text = await resp.text()
                    pattern = rf'/@{_re.escape(username)}/video/(\d+)'
                    video_ids = _re.findall(pattern, text, _re.IGNORECASE)
                    seen = set()
                    for vid in video_ids:
                        if vid in seen:
                            continue
                        seen.add(vid)
                        items.append({
                            "source": "tiktok",
                            "id": f"tiktok:{vid}",
                            "username": username,
                            "title": f"New TikTok from @{username}",
                            "url": f"https://www.tiktok.com/@{username}/video/{vid}",
                        })
                        if len(seen) >= 5:
                            break
                except Exception:
                    continue
    except Exception:
        traceback.print_exc()
    return items


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

def _resolve_channel_for_creator(bot, guild, creator_map: dict[str, int], creator_key: str):
    """Return the Discord channel for a creator using the channel mapping."""
    ch_id = creator_map.get(creator_key.lower(), 0)
    if ch_id:
        ch = bot.get_channel(ch_id) or guild.get_channel(ch_id)
        if ch:
            return ch
    return None


class SocialMedia(commands.Cog):
    """Monitors social media and posts notifications to configured channels.

    Uses a per-channel model: each platform has a CHANNELS list where each
    entry maps one Discord channel to one or more creators.
    """

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
        for source_name in PLATFORMS:
            src = cfg.get(source_name, {})
            if not isinstance(src, dict):
                continue
            enabled = bool(src.get("ENABLED", False))
            channels = _channels_list(src)
            icon = "✅" if enabled else "❌"
            if channels:
                ch_count = len(channels)
                creator_count = len(_all_creators(src))
                base = (
                    f"{icon} **{source_name.title()}** — "
                    f"{ch_count} channel{'s' if ch_count != 1 else ''}, "
                    f"{creator_count} creator{'s' if creator_count != 1 else ''}"
                )
            else:
                base = f"{icon} **{source_name.title()}** — Not configured"
            lines.append(base)

        if not lines:
            lines.append(translate("socials.sources.none", guild_id=guild_id,
                                   default="No social media sources configured."))

        embed = discord.Embed(
            title=translate("socials.sources.title", guild_id=guild_id,
                            default="📡 Social Media Sources"),
            description="\n".join(lines),
            color=discord.Color.purple(),
        )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # /socialchannels — show per-channel creator assignments
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="socialchannels",
        description="Show all social media channel → creator assignments.",
    )
    async def socialchannels(self, ctx: commands.Context):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        cfg = _cfg(guild_id)

        lines = []
        for source_name in PLATFORMS:
            src = cfg.get(source_name, {})
            if not isinstance(src, dict):
                continue
            channels = _channels_list(src)
            if not channels:
                continue
            lines.append(f"**{source_name.title()}:**")
            for entry in channels:
                ch_id = entry.get("CHANNEL_ID", 0)
                ch_name = entry.get("CHANNEL_NAME", "")
                creators = entry.get("CREATORS", [])
                creator_str = ", ".join(creators) if creators else "(none)"
                display = f"  <#{ch_id}>" if ch_id else f"  #{ch_name or '?'}"
                lines.append(f"{display}: {creator_str}")

        if not lines:
            lines.append(translate("socials.channels.none", guild_id=guild_id,
                                   default="No social media channels configured."))

        embed = discord.Embed(
            title=translate("socials.channels.title", guild_id=guild_id,
                            default="📡 Social Media Channels"),
            description="\n".join(lines),
            color=discord.Color.purple(),
        )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # /socialadd — add a creator to a channel
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="socialadd",
        description="Add a creator to a Discord channel for notifications.",
    )
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        platform="Platform (twitch, youtube, tiktok, twitter)",
        creator="Creator name (Twitch/TikTok username, YouTube channel ID, Twitter handle)",
        channel="Discord text channel for notifications",
    )
    @app_commands.choices(platform=PLATFORM_CHOICES)
    async def socialadd(
        self,
        ctx: commands.Context,
        platform: str,
        creator: str,
        channel: discord.TextChannel,
    ):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        if guild_id is None:
            await ctx.send("❌ Server-only command.")
            return

        platform_upper = platform.strip().upper()
        if platform_upper not in PLATFORMS:
            await ctx.send(translate("socials.error.platform", guild_id=guild_id,
                                     default="❌ Platform must be one of: twitch, youtube, tiktok, twitter"))
            return

        cfg_path = guild_data_path(guild_id, "social_media.json")
        if not cfg_path:
            await ctx.send("❌ Could not resolve config path.")
            return

        cfg = safe_load_json(cfg_path, default={})
        src = cfg.setdefault(platform_upper, {})
        channels = src.setdefault("CHANNELS", [])

        creator_clean = creator.strip()
        creator_lower = creator_clean.lower()

        # Find or create channel entry
        entry = None
        for e in channels:
            if isinstance(e, dict) and int(e.get("CHANNEL_ID", 0) or 0) == channel.id:
                entry = e
                break

        if entry is None:
            entry = {"CHANNEL_NAME": channel.name, "CHANNEL_ID": channel.id, "CREATORS": []}
            channels.append(entry)

        creators = entry.setdefault("CREATORS", [])
        existing_lower = [c.lower() for c in creators]
        if creator_lower in existing_lower:
            await ctx.send(translate(
                "socials.add.exists", guild_id=guild_id,
                default="ℹ️ **{creator}** is already assigned to {channel}.",
                creator=creator_clean, channel=channel.mention,
            ))
            return

        creators.append(creator_clean)
        safe_save_json(cfg_path, cfg)
        await ctx.send(translate(
            "socials.add.ok", guild_id=guild_id,
            default="✅ **{creator}** ({platform}) → {channel}",
            creator=creator_clean, platform=platform_upper.title(), channel=channel.mention,
        ))

    # ------------------------------------------------------------------
    # /socialremove — remove a creator from a channel
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="socialremove",
        description="Remove a creator from a Discord channel.",
    )
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        platform="Platform (twitch, youtube, tiktok, twitter)",
        creator="Creator name to remove",
    )
    @app_commands.choices(platform=PLATFORM_CHOICES)
    async def socialremove(
        self,
        ctx: commands.Context,
        platform: str,
        creator: str,
    ):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        if guild_id is None:
            await ctx.send("❌ Server-only command.")
            return

        platform_upper = platform.strip().upper()
        if platform_upper not in PLATFORMS:
            await ctx.send(translate("socials.error.platform", guild_id=guild_id,
                                     default="❌ Platform must be one of: twitch, youtube, tiktok, twitter"))
            return

        cfg_path = guild_data_path(guild_id, "social_media.json")
        if not cfg_path:
            await ctx.send("❌ Could not resolve config path.")
            return

        cfg = safe_load_json(cfg_path, default={})
        src = cfg.get(platform_upper, {})
        channels = src.get("CHANNELS", [])

        creator_lower = creator.strip().lower()
        found = False
        for entry in channels:
            if not isinstance(entry, dict):
                continue
            creators = entry.get("CREATORS", [])
            new_creators = [c for c in creators if c.lower() != creator_lower]
            if len(new_creators) < len(creators):
                entry["CREATORS"] = new_creators
                found = True

        # Remove empty channel entries
        src["CHANNELS"] = [e for e in channels if isinstance(e, dict) and e.get("CREATORS")]
        cfg[platform_upper] = src
        safe_save_json(cfg_path, cfg)

        if found:
            await ctx.send(translate(
                "socials.remove.ok", guild_id=guild_id,
                default="✅ **{creator}** removed from {platform}.",
                creator=creator.strip(), platform=platform_upper.title(),
            ))
        else:
            await ctx.send(translate(
                "socials.remove.notfound", guild_id=guild_id,
                default="ℹ️ **{creator}** was not found in {platform}.",
                creator=creator.strip(), platform=platform_upper.title(),
            ))

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
            creator_map = _creator_to_channel_id(twitch_cfg)
            usernames = _all_creators(twitch_cfg)
            client_id = str(twitch_cfg.get("CLIENT_ID", "") or "")
            oauth_token = str(twitch_cfg.get("OAUTH_TOKEN", "") or "")
            if usernames and client_id and oauth_token:
                streams = await _fetch_twitch_streams(usernames, client_id, oauth_token)
                posted_set = set(posted_data.get("twitch", []))
                for stream in streams:
                    sid = stream["id"]
                    if sid in posted_set:
                        continue
                    target_ch = _resolve_channel_for_creator(
                        self.bot, guild, creator_map,
                        stream.get("username", "").lower(),
                    )
                    if not target_ch:
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
                        await target_ch.send(embed=embed)
                        posted_data.setdefault("twitch", []).append(sid)
                        total_new += 1
                    except Exception as exc:
                        print(f"[SocialMedia] Twitch post failed: {exc}")

        # --- YouTube ---
        youtube_cfg = cfg.get("YOUTUBE", {})
        if isinstance(youtube_cfg, dict) and youtube_cfg.get("ENABLED"):
            creator_map = _creator_to_channel_id(youtube_cfg)
            yt_channel_ids = _all_creators(youtube_cfg)
            if yt_channel_ids:
                videos = await _fetch_youtube_latest(yt_channel_ids)
                posted_set = set(posted_data.get("youtube", []))
                for video in videos:
                    vid = video["id"]
                    if vid in posted_set:
                        continue
                    # For YouTube, try matching by author name (lowercase) first,
                    # but the creator list holds channel IDs, so try both.
                    author_key = (video.get("author") or "").lower()
                    target_ch = _resolve_channel_for_creator(self.bot, guild, creator_map, author_key)
                    if not target_ch:
                        # Try matching the YouTube channel ID itself from the video URL
                        for yt_cid in yt_channel_ids:
                            target_ch = _resolve_channel_for_creator(self.bot, guild, creator_map, yt_cid.lower())
                            if target_ch:
                                break
                    if not target_ch:
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
                        await target_ch.send(embed=embed)
                        posted_data.setdefault("youtube", []).append(vid)
                        total_new += 1
                    except Exception as exc:
                        print(f"[SocialMedia] YouTube post failed: {exc}")

        # --- Twitter/X ---
        twitter_cfg = cfg.get("TWITTER", {})
        if isinstance(twitter_cfg, dict) and twitter_cfg.get("ENABLED"):
            # Twitter/X API requires Bearer token; placeholder for future implementation
            pass

        # --- TikTok ---
        tiktok_cfg = cfg.get("TIKTOK", {})
        if isinstance(tiktok_cfg, dict) and tiktok_cfg.get("ENABLED"):
            creator_map = _creator_to_channel_id(tiktok_cfg)
            usernames = _all_creators(tiktok_cfg)
            if usernames:
                videos = await _fetch_tiktok_latest(usernames)
                posted_set = set(posted_data.get("tiktok", []))
                for video in videos:
                    vid = video["id"]
                    if vid in posted_set:
                        continue
                    target_ch = _resolve_channel_for_creator(
                        self.bot, guild, creator_map,
                        (video.get("username") or "").lower(),
                    )
                    if not target_ch:
                        continue
                    embed = discord.Embed(
                        title=f"\U0001f3b5 {video['username']} posted a new TikTok!",
                        description=f"**{video['title']}**",
                        url=video["url"],
                        color=discord.Color.from_rgb(0, 0, 0),
                        timestamp=datetime.now(timezone.utc),
                    )
                    try:
                        await target_ch.send(embed=embed)
                        posted_data.setdefault("tiktok", []).append(vid)
                        total_new += 1
                    except Exception as exc:
                        print(f"[SocialMedia] TikTok post failed: {exc}")

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
