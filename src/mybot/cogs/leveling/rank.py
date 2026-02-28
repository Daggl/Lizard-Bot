"""Rank cog with fully customizable card rendering."""

from __future__ import annotations

import io
import json
import os
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from mybot.utils.config_store import config_json_path, load_json_dict
from mybot.utils.i18n import translate
from mybot.utils.paths import REPO_ROOT

from .levels import xp_for_level

# ======================================================
# CANVAS CONSTANTS
# ======================================================

CARD_WIDTH = 1500
CARD_HEIGHT = 550  # enforce 1500x550 everywhere

BAR_WIDTH = 900
BAR_HEIGHT = 38

AVATAR_SIZE = 300

FONT_BOLD = "assets/fonts/Poppins-Bold.ttf"
FONT_REGULAR = "assets/fonts/Poppins-Regular.ttf"

# Default element anchors (can be overridden in config)
DEFAULT_POS = {
    "avatar_x": 75,
    "avatar_y": 125,
    "username_x": 400,
    "username_y": 80,
    "level_x": 400,
    "level_y": 200,
    "xp_x": 1065,
    "xp_y": 270,
    "bar_x": 400,
    "bar_y": 330,
    "messages_x": 400,
    "messages_y": 400,
    "voice_x": 680,
    "voice_y": 400,
    "achievements_x": 980,
    "achievements_y": 400,
}


# ======================================================
# HELPERS
# ======================================================


def _safe_truetype(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font path relative to repo root with fallback."""
    try:
        resolved = path
        if path and not os.path.isabs(path):
            resolved = os.path.join(REPO_ROOT, path)
        if resolved and os.path.exists(resolved):
            return ImageFont.truetype(resolved, max(8, int(size or 8)))
    except Exception:
        pass
    return ImageFont.load_default()


def _parse_hex_color(value: str | None, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    """Parse hex color strings into RGB tuples."""
    try:
        s = (value or "").strip()
        if s.startswith("#"):
            s = s[1:]
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) != 6:
            return fallback
        return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return fallback


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    val = _to_int(value, default)
    return max(minimum, min(maximum, val))


def _load_rank_cfg(guild_id: int | str | None = None) -> dict:
    """Load rank config with guild-specific override."""
    try:
        if guild_id is not None:
            guild_path = config_json_path(REPO_ROOT, "rank.json", guild_id=guild_id)
            if guild_path and os.path.exists(guild_path):
                return load_json_dict(guild_path) or {}
        fallback = os.path.join(REPO_ROOT, "config", "rank.json")
        if os.path.exists(fallback):
            with open(fallback, "r", encoding="utf-8") as fh:
                return json.load(fh) or {}
    except Exception:
        pass
    return {}


def _compose_rank_background(
    path: str | None,
    width: int,
    height: int,
    mode: str,
    zoom_percent: int,
    offset_x: int,
    offset_y: int,
) -> Image.Image:
    """Compose a background respecting the requested mode."""
    canvas = Image.new("RGB", (width, height), (18, 18, 18))

    resolved = path or "assets/rankcard.png"
    if resolved and not os.path.isabs(resolved):
        resolved = os.path.join(REPO_ROOT, resolved)

    try:
        if not resolved or not os.path.exists(resolved):
            return canvas
        src = Image.open(resolved).convert("RGB")
    except Exception:
        return canvas

    src_w, src_h = src.size
    if not src_w or not src_h:
        return canvas

    mode_norm = str(mode or "cover").lower()
    if mode_norm not in ("cover", "contain", "stretch"):
        mode_norm = "cover"

    try:
        zoom = max(10, min(400, int(zoom_percent or 100)))
    except Exception:
        zoom = 100

    resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)

    if mode_norm == "stretch":
        canvas.paste(src.resize((width, height), resampling), (0, 0))
        return canvas

    base_scale = max(width / src_w, height / src_h) if mode_norm == "cover" else min(width / src_w, height / src_h)
    scale = base_scale * (zoom / 100.0)

    new_size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
    fitted = src.resize(new_size, resampling)

    paste_x = (width - new_size[0]) // 2 + int(offset_x or 0)
    paste_y = (height - new_size[1]) // 2 + int(offset_y or 0)
    canvas.paste(fitted, (paste_x, paste_y))
    return canvas


# ======================================================
# RENDERER (also used by UI preview)
# ======================================================


def render_rankcard(
    *,
    bg_path: str | None = "assets/rankcard.png",
    bg_mode: str = "cover",
    bg_zoom: int = 100,
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
    username: str = "Username",
    level: int = 1,
    xp: int = 0,
    xp_needed: int = 150,
    messages: int = 0,
    voice_minutes: int = 0,
    achievements_count: int = 0,
    avatar_bytes: Optional[bytes] = None,
    avatar_x: int = DEFAULT_POS["avatar_x"],
    avatar_y: int = DEFAULT_POS["avatar_y"],
    avatar_size: int = AVATAR_SIZE,
    username_x: int = DEFAULT_POS["username_x"],
    username_y: int = DEFAULT_POS["username_y"],
    username_font: str = FONT_BOLD,
    username_font_size: int = 90,
    username_color: str = "#FFFFFF",
    level_x: int = DEFAULT_POS["level_x"],
    level_y: int = DEFAULT_POS["level_y"],
    level_font: str = FONT_REGULAR,
    level_font_size: int = 60,
    level_color: str = "#C8C8C8",
    xp_x: int = DEFAULT_POS["xp_x"],
    xp_y: int = DEFAULT_POS["xp_y"],
    xp_font: str = FONT_REGULAR,
    xp_font_size: int = 33,
    xp_color: str = "#C8C8C8",
    bar_x: int = DEFAULT_POS["bar_x"],
    bar_y: int = DEFAULT_POS["bar_y"],
    bar_width: int = BAR_WIDTH,
    bar_height: int = BAR_HEIGHT,
    bar_bg_color: str = "#323232",
    bar_fill_color: str = "#8C6EFF",
    messages_x: int = DEFAULT_POS["messages_x"],
    messages_y: int = DEFAULT_POS["messages_y"],
    messages_font: str = FONT_REGULAR,
    messages_font_size: int = 33,
    messages_color: str = "#C8C8C8",
    voice_x: int = DEFAULT_POS["voice_x"],
    voice_y: int = DEFAULT_POS["voice_y"],
    voice_font: str = FONT_REGULAR,
    voice_font_size: int = 33,
    voice_color: str = "#C8C8C8",
    achievements_x: int = DEFAULT_POS["achievements_x"],
    achievements_y: int = DEFAULT_POS["achievements_y"],
    achievements_font: str = FONT_REGULAR,
    achievements_font_size: int = 33,
    achievements_color: str = "#C8C8C8",
    guild_id: int | str | None = None,
) -> bytes:
    """Render rank card and return PNG bytes (used by bot + UI)."""

    avatar_size = _clamp_int(avatar_size, 16, 2000, AVATAR_SIZE)
    bar_width = _clamp_int(bar_width, 1, 10000, BAR_WIDTH)
    bar_height = _clamp_int(bar_height, 1, 2000, BAR_HEIGHT)

    avatar_x = _to_int(avatar_x, DEFAULT_POS["avatar_x"])
    avatar_y = _to_int(avatar_y, DEFAULT_POS["avatar_y"])
    username_x = _to_int(username_x, DEFAULT_POS["username_x"])
    username_y = _to_int(username_y, DEFAULT_POS["username_y"])
    level_x = _to_int(level_x, DEFAULT_POS["level_x"])
    level_y = _to_int(level_y, DEFAULT_POS["level_y"])
    xp_x = _to_int(xp_x, DEFAULT_POS["xp_x"])
    xp_y = _to_int(xp_y, DEFAULT_POS["xp_y"])
    bar_x = _to_int(bar_x, DEFAULT_POS["bar_x"])
    bar_y = _to_int(bar_y, DEFAULT_POS["bar_y"])
    messages_x = _to_int(messages_x, DEFAULT_POS["messages_x"])
    messages_y = _to_int(messages_y, DEFAULT_POS["messages_y"])
    voice_x = _to_int(voice_x, DEFAULT_POS["voice_x"])
    voice_y = _to_int(voice_y, DEFAULT_POS["voice_y"])
    achievements_x = _to_int(achievements_x, DEFAULT_POS["achievements_x"])
    achievements_y = _to_int(achievements_y, DEFAULT_POS["achievements_y"])

    card = _compose_rank_background(
        bg_path,
        CARD_WIDTH,
        CARD_HEIGHT,
        bg_mode,
        bg_zoom,
        bg_offset_x,
        bg_offset_y,
    )
    draw = ImageDraw.Draw(card)

    # Avatar
    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA") if avatar_bytes else None
    except Exception:
        avatar = None
    if avatar is None:
        avatar = Image.new("RGBA", (avatar_size, avatar_size), (100, 100, 100, 255))
    avatar = avatar.resize((avatar_size, avatar_size))
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar.putalpha(mask)
    card.paste(avatar, (avatar_x, avatar_y), avatar)

    # Fonts + colors
    font_username = _safe_truetype(username_font, username_font_size)
    font_level = _safe_truetype(level_font, level_font_size)
    font_xp = _safe_truetype(xp_font, xp_font_size)
    font_messages = _safe_truetype(messages_font, messages_font_size)
    font_voice = _safe_truetype(voice_font, voice_font_size)
    font_achievements = _safe_truetype(achievements_font, achievements_font_size)

    color_username = _parse_hex_color(username_color, (255, 255, 255))
    color_level = _parse_hex_color(level_color, (200, 200, 200))
    color_xp = _parse_hex_color(xp_color, (200, 200, 200))
    color_messages = _parse_hex_color(messages_color, (200, 200, 200))
    color_voice = _parse_hex_color(voice_color, (200, 200, 200))
    color_achievements = _parse_hex_color(achievements_color, (200, 200, 200))
    color_bar_bg = _parse_hex_color(bar_bg_color, (50, 50, 50))
    color_bar_fill = _parse_hex_color(bar_fill_color, (140, 110, 255))

    # Username + Level + XP text
    draw.text((username_x, username_y), username, font=font_username, fill=color_username)

    level_text = translate("rank.card.level", guild_id=guild_id, level=level, default=f"Level {level}")
    draw.text((level_x, level_y), level_text, font=font_level, fill=color_level)

    xp_text = translate("rank.card.xp_progress", guild_id=guild_id, current=xp, needed=xp_needed, default=f"{xp}/{xp_needed} XP")
    draw.text((xp_x, xp_y), xp_text, font=font_xp, fill=color_xp)

    # Progress bar
    xp = _to_int(xp, 0)
    xp_needed = _to_int(xp_needed, 0)
    progress = 0 if xp_needed <= 0 else max(0.0, min(1.0, xp / xp_needed))
    draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), fill=color_bar_bg)
    draw.rectangle((bar_x, bar_y, bar_x + int(bar_width * progress), bar_y + bar_height), fill=color_bar_fill)

    # Stats
    messages_text = translate("rank.card.messages", guild_id=guild_id, value=messages, default=f"💬 {messages}")
    draw.text((messages_x, messages_y), messages_text, font=font_messages, fill=color_messages)

    voice_text = translate("rank.card.voice", guild_id=guild_id, value=voice_minutes, default=f"🎤 {voice_minutes}m")
    draw.text((voice_x, voice_y), voice_text, font=font_voice, fill=color_voice)

    achievements_text = translate(
        "rank.card.achievements",
        guild_id=guild_id,
        value=achievements_count,
        default=f"🏆 {achievements_count}",
    )
    draw.text((achievements_x, achievements_y), achievements_text, font=font_achievements, fill=color_achievements)

    buffer = io.BytesIO()
    card.save(buffer, "PNG")
    return buffer.getvalue()


# ======================================================
# RANK COG
# ======================================================


class Rank(commands.Cog):
    """Rank card rendering + admin xp commands."""

    def __init__(self, bot):
        self.bot = bot

    def _build_achievements_embed(self, member, achievements: list[str]):
        guild_id = getattr(getattr(member, "guild", None), "id", None)
        embed = discord.Embed(
            title=translate("rank.embed.achievements.title", guild_id=guild_id, member=member.display_name),
            color=discord.Color.blurple(),
        )
        cleaned = [str(a).strip() for a in (achievements or []) if str(a).strip()]
        embed.description = "\n".join(f"• {item}" for item in cleaned) if cleaned else translate(
            "rank.embed.achievements.empty",
            guild_id=guild_id,
        )
        return embed

    # ==================================================
    # USER COMMANDS
    # ==================================================

    @commands.hybrid_command(description="Show your rank.")
    async def rank(self, ctx, member: discord.Member | None = None):
        target = member or ctx.author
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        user = self.bot.db.get_user(target.id, guild_id=guild_id)
        file = await self.generate_rankcard(target)
        await ctx.send(file=file)
        await ctx.send(embed=self._build_achievements_embed(target, user.get("achievements", [])))

    @commands.hybrid_command(description="Show the level leaderboard.")
    async def leaderboard(self, ctx, top: int = 10):
        guild = ctx.guild
        guild_id = getattr(guild, "id", None)
        data = self.bot.db._load_guild(guild_id)
        ranking = sorted(data.items(), key=lambda item: (item[1].get("level", 1), item[1].get("xp", 0)), reverse=True)
        top = max(1, min(top, 25))
        ranking = ranking[:top]
        if not ranking:
            await ctx.send(translate("rank.msg.leaderboard_empty", guild_id=guild_id, default="No users found."))
            return
        embed = discord.Embed(
            title=translate("rank.embed.leaderboard_title", guild_id=guild_id, default="🏆 Level Leaderboard"),
            color=0xFFD700,
        )
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []
        for idx, (user_id, user_data) in enumerate(ranking, 1):
            level = user_data.get("level", 1)
            xp = user_data.get("xp", 0)
            handle = guild.get_member(int(user_id)) if guild else None
            name = handle.display_name if handle else f"User {user_id}"
            medal = medals.get(idx, f"**{idx}.**")
            lines.append(f"{medal} {name} — Level **{level}** ({xp} XP)")
        embed.description = "\n".join(lines)
        if guild:
            embed.set_footer(text=guild.name)
        await ctx.send(embed=embed)

    @commands.hybrid_command(description="Show another user's rank (admin).")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def rankuser(self, ctx, member: discord.Member):
        file = await self.generate_rankcard(member)
        await ctx.send(file=file)

    # ==================================================
    # CARD GENERATION
    # ==================================================

    async def generate_rankcard(self, member: discord.Member) -> discord.File:
        guild_id = getattr(getattr(member, "guild", None), "id", None)
        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        cfg = _load_rank_cfg(guild_id=guild_id)

        avatar_bytes: bytes | None = None
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(member.display_avatar.url) as resp:
                    if resp.status == 200:
                        avatar_bytes = await resp.read()
        except Exception:
            avatar_bytes = None

        def conf(key: str, default):
            return cfg.get(key, default)

        text_off_x = int(cfg.get("TEXT_OFFSET_X", 0) or 0)
        text_off_y = int(cfg.get("TEXT_OFFSET_Y", 0) or 0)
        avatar_off_x = int(cfg.get("AVATAR_OFFSET_X", 0) or 0)
        avatar_off_y = int(cfg.get("AVATAR_OFFSET_Y", 0) or 0)
        info_font_legacy = conf("INFO_FONT", FONT_REGULAR)
        info_size_legacy = conf("INFO_FONT_SIZE", 60)
        info_color_legacy = conf("INFO_COLOR", "#C8C8C8")

        png_bytes = render_rankcard(
            bg_path=conf("BG_PATH", "assets/rankcard.png"),
            bg_mode=conf("BG_MODE", "cover"),
            bg_zoom=conf("BG_ZOOM", 100),
            bg_offset_x=conf("BG_OFFSET_X", 0),
            bg_offset_y=conf("BG_OFFSET_Y", 0),
            username=member.display_name,
            level=_to_int(user.get("level", 1), 1),
            xp=_to_int(user.get("xp", 0), 0),
            xp_needed=xp_for_level(_to_int(user.get("level", 1), 1), guild_id=guild_id),
            messages=_to_int(user.get("messages", 0), 0),
            voice_minutes=max(0, _to_int(user.get("voice_time", 0), 0) // 60),
            achievements_count=len(user.get("achievements", []) or []),
            avatar_bytes=avatar_bytes,
            avatar_x=conf("AVATAR_X", DEFAULT_POS["avatar_x"] + avatar_off_x),
            avatar_y=conf("AVATAR_Y", DEFAULT_POS["avatar_y"] + avatar_off_y),
            avatar_size=conf("AVATAR_SIZE", AVATAR_SIZE),
            username_x=conf("USERNAME_X", DEFAULT_POS["username_x"] + text_off_x),
            username_y=conf("USERNAME_Y", DEFAULT_POS["username_y"] + text_off_y),
            username_font=conf("USERNAME_FONT", conf("NAME_FONT", FONT_BOLD)),
            username_font_size=conf("USERNAME_FONT_SIZE", conf("NAME_FONT_SIZE", 90)),
            username_color=conf("USERNAME_COLOR", conf("NAME_COLOR", "#FFFFFF")),
            level_x=conf("LEVEL_X", DEFAULT_POS["level_x"] + text_off_x),
            level_y=conf("LEVEL_Y", DEFAULT_POS["level_y"] + text_off_y),
            level_font=conf("LEVEL_FONT", info_font_legacy),
            level_font_size=conf("LEVEL_FONT_SIZE", info_size_legacy),
            level_color=conf("LEVEL_COLOR", info_color_legacy),
            xp_x=conf("XP_X", DEFAULT_POS["xp_x"] + text_off_x),
            xp_y=conf("XP_Y", DEFAULT_POS["xp_y"] + text_off_y),
            xp_font=conf("XP_FONT", info_font_legacy),
            xp_font_size=conf("XP_FONT_SIZE", 33),
            xp_color=conf("XP_COLOR", info_color_legacy),
            bar_x=conf("BAR_X", DEFAULT_POS["bar_x"]),
            bar_y=conf("BAR_Y", DEFAULT_POS["bar_y"]),
            bar_width=conf("BAR_WIDTH", BAR_WIDTH),
            bar_height=conf("BAR_HEIGHT", BAR_HEIGHT),
            bar_bg_color=conf("BAR_BG_COLOR", "#323232"),
            bar_fill_color=conf("BAR_FILL_COLOR", conf("BAR_COLOR", "#8C6EFF")),
            messages_x=conf("MESSAGES_X", DEFAULT_POS["messages_x"] + text_off_x),
            messages_y=conf("MESSAGES_Y", DEFAULT_POS["messages_y"] + text_off_y),
            messages_font=conf("MESSAGES_FONT", info_font_legacy),
            messages_font_size=conf("MESSAGES_FONT_SIZE", 33),
            messages_color=conf("MESSAGES_COLOR", info_color_legacy),
            voice_x=conf("VOICE_X", DEFAULT_POS["voice_x"] + text_off_x),
            voice_y=conf("VOICE_Y", DEFAULT_POS["voice_y"] + text_off_y),
            voice_font=conf("VOICE_FONT", info_font_legacy),
            voice_font_size=conf("VOICE_FONT_SIZE", 33),
            voice_color=conf("VOICE_COLOR", info_color_legacy),
            achievements_x=conf("ACHIEVEMENTS_X", DEFAULT_POS["achievements_x"] + text_off_x),
            achievements_y=conf("ACHIEVEMENTS_Y", DEFAULT_POS["achievements_y"] + text_off_y),
            achievements_font=conf("ACHIEVEMENTS_FONT", info_font_legacy),
            achievements_font_size=conf("ACHIEVEMENTS_FONT_SIZE", 33),
            achievements_color=conf("ACHIEVEMENTS_COLOR", info_color_legacy),
            guild_id=guild_id,
        )

        return discord.File(io.BytesIO(png_bytes), filename="rank.png")

    # ==================================================
    # ADMIN COMMANDS
    # ==================================================

    @commands.hybrid_command(description="Give XP to a user.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def addxp(self, ctx, member: discord.Member, amount: int):
        levels = self.bot.get_cog("Levels")
        if levels:
            await levels.add_xp(member, amount)
        achievements = self.bot.get_cog("Achievements")
        if achievements:
            await achievements.check_achievements(member)
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        await ctx.send(
            translate(
                "rank.msg.addxp",
                guild_id=guild_id,
                amount=amount,
                member=member.mention,
            )
        )

    @commands.hybrid_command(description="Remove XP from a user.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def removexp(self, ctx, member: discord.Member, amount: int):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        user["xp"] = max(0, user["xp"] - amount)
        self.bot.db.save(guild_id=guild_id)
        await ctx.send(
            translate(
                "rank.msg.removexp",
                guild_id=guild_id,
                amount=amount,
                member=member.mention,
            )
        )

    @commands.hybrid_command(description="Reset a user's level data.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx, member: discord.Member):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        user.update({
            "xp": 0,
            "level": 1,
            "messages": 0,
            "voice_time": 0,
            "achievements": [],
        })
        self.bot.db.save(guild_id=guild_id)
        await ctx.send(translate("rank.msg.reset", guild_id=guild_id))


async def setup(bot):
    await bot.add_cog(Rank(bot))
