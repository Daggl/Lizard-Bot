import io
import json
import os

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from mybot.utils.config_store import config_json_path, load_json_dict
from mybot.utils.i18n import translate
from mybot.utils.paths import REPO_ROOT

from .levels import xp_for_level

CARD_WIDTH = 1000
CARD_HEIGHT = 300

BAR_WIDTH = 600
BAR_HEIGHT = 25

AVATAR_SIZE = 180

FONT_BOLD = "assets/fonts/Poppins-Bold.ttf"
FONT_REGULAR = "assets/fonts/Poppins-Regular.ttf"


def _safe_truetype(path: str, size: int):
    try:
        if path:
            return ImageFont.truetype(path, max(8, int(size or 8)))
    except Exception:
        pass
    return ImageFont.load_default()


def _parse_hex_color(value, fallback):
    try:
        s = str(value or "").strip()
        if s.startswith("#"):
            s = s[1:]
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) != 6:
            return fallback
        return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return fallback


def _load_rank_cfg(guild_id: int | str | None = None) -> dict:
    """Load rank config, trying guild-specific override first."""
    try:
        if guild_id is not None:
            guild_path = config_json_path(REPO_ROOT, "rank.json", guild_id=guild_id)
            if os.path.exists(guild_path):
                return load_json_dict(guild_path) or {}
        cfg_path = os.path.join(REPO_ROOT, "config", "rank.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as fh:
                return json.load(fh) or {}
    except Exception:
        pass
    return {}


def _compose_rank_background(path: str, mode: str, zoom_percent: int, offset_x: int, offset_y: int) -> Image.Image:
    canvas = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (18, 18, 18))
    try:
        src = Image.open(path).convert("RGB")
    except Exception:
        return canvas

    src_w, src_h = src.size
    if src_w <= 0 or src_h <= 0:
        return canvas

    mode_norm = str(mode or "cover").strip().lower()
    if mode_norm not in ("cover", "contain", "stretch"):
        mode_norm = "cover"

    try:
        zoom = int(zoom_percent or 100)
    except Exception:
        zoom = 100
    zoom = max(10, min(400, zoom))

    resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

    if mode_norm == "stretch":
        stretched = src.resize((CARD_WIDTH, CARD_HEIGHT), resampling)
        canvas.paste(stretched, (0, 0))
        return canvas

    if mode_norm == "cover":
        base_scale = max(CARD_WIDTH / float(src_w), CARD_HEIGHT / float(src_h))
    else:
        base_scale = min(CARD_WIDTH / float(src_w), CARD_HEIGHT / float(src_h))

    scale = base_scale * (zoom / 100.0)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    fitted = src.resize((new_w, new_h), resampling)

    x = (CARD_WIDTH - new_w) // 2 + int(offset_x or 0)
    y = (CARD_HEIGHT - new_h) // 2 + int(offset_y or 0)
    canvas.paste(fitted, (x, y))
    return canvas


class Rank(commands.Cog):
    """Rank card and admin XP commands."""

    def __init__(self, bot):
        self.bot = bot

    def _build_achievements_embed(self, member, achievements: list[str]) -> discord.Embed:
        guild_id = getattr(getattr(member, "guild", None), "id", None)
        embed = discord.Embed(
            title=translate("rank.embed.achievements.title", guild_id=guild_id, member=member.display_name),
            color=discord.Color.blurple(),
        )

        cleaned = [str(a).strip() for a in (achievements or []) if str(a).strip()]
        if cleaned:
            embed.description = "\n".join(f"• {name}" for name in cleaned)
        else:
            embed.description = translate("rank.embed.achievements.empty", guild_id=guild_id)

        return embed

    # ======================================================
    # USER COMMAND
    # ======================================================

    @commands.hybrid_command(description="Rank command.")
    async def rank(self, ctx, member: discord.Member = None):
        """User rank card."""

        member = member or ctx.author
        guild_id = getattr(getattr(ctx, 'guild', None), 'id', None)

        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        achievements = user.get("achievements", [])

        file = await self.generate_rankcard(member)

        await ctx.send(file=file)
        await ctx.send(embed=self._build_achievements_embed(member, achievements))

    # ======================================================
    # ADMIN COMMAND - rankuser
    # ======================================================

    @commands.hybrid_command(description="Rankuser command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def rankuser(self, ctx, member: discord.Member):
        """Admin rank card command."""

        file = await self.generate_rankcard(member)

        await ctx.send(file=file)

    # ======================================================
    # GENERATE CARD
    # ======================================================

    async def generate_rankcard(
        self,
        member,
        bg_path: str = None,
        bg_mode: str = None,
        bg_zoom: int = None,
        bg_offset_x: int = None,
        bg_offset_y: int = None,
        name_font: str = None,
        info_font: str = None,
        name_font_size: int = None,
        info_font_size: int = None,
        name_color: str = None,
        info_color: str = None,
        text_offset_x: int = None,
        text_offset_y: int = None,
    ):
        guild_id = getattr(getattr(member, 'guild', None), 'id', None)

        user = self.bot.db.get_user(member.id, guild_id=guild_id)

        level = user["level"]
        xp = user["xp"]
        needed = xp_for_level(level)

        progress = xp / needed if needed > 0 else 0

        messages = user["messages"]
        voice_minutes = user["voice_time"] // 60
        achievements = len(user["achievements"])

        cfg = _load_rank_cfg(guild_id=getattr(getattr(member, 'guild', None), 'id', None))
        resolved_bg_path = bg_path or cfg.get("BG_PATH") or "assets/rankcard.png"
        resolved_bg_mode = bg_mode or cfg.get("BG_MODE", "cover")
        resolved_bg_zoom = bg_zoom if bg_zoom is not None else cfg.get("BG_ZOOM", 100)
        resolved_bg_x = bg_offset_x if bg_offset_x is not None else cfg.get("BG_OFFSET_X", 0)
        resolved_bg_y = bg_offset_y if bg_offset_y is not None else cfg.get("BG_OFFSET_Y", 0)
        resolved_name_font = name_font or cfg.get("NAME_FONT", FONT_BOLD)
        resolved_info_font = info_font or cfg.get("INFO_FONT", FONT_REGULAR)
        resolved_name_size = int(name_font_size if name_font_size is not None else cfg.get("NAME_FONT_SIZE", 60) or 60)
        resolved_info_size = int(info_font_size if info_font_size is not None else cfg.get("INFO_FONT_SIZE", 40) or 40)
        resolved_name_color = _parse_hex_color(name_color if name_color is not None else cfg.get("NAME_COLOR", "#FFFFFF"), (255, 255, 255))
        resolved_info_color = _parse_hex_color(info_color if info_color is not None else cfg.get("INFO_COLOR", "#C8C8C8"), (200, 200, 200))
        resolved_text_x = int(text_offset_x if text_offset_x is not None else cfg.get("TEXT_OFFSET_X", 0) or 0)
        resolved_text_y = int(text_offset_y if text_offset_y is not None else cfg.get("TEXT_OFFSET_Y", 0) or 0)

        default_rank_abs = os.path.abspath(os.path.join(REPO_ROOT, "assets", "rankcard.png"))
        requested_rank_abs = os.path.abspath(
            resolved_bg_path if os.path.isabs(str(resolved_bg_path or "")) else os.path.join(REPO_ROOT, str(resolved_bg_path or ""))
        )

        if requested_rank_abs.lower() == default_rank_abs.lower() and os.path.exists(requested_rank_abs):
            try:
                card = Image.open(requested_rank_abs).convert("RGB")
            except Exception:
                card = _compose_rank_background(
                    resolved_bg_path,
                    resolved_bg_mode,
                    int(resolved_bg_zoom or 100),
                    int(resolved_bg_x or 0),
                    int(resolved_bg_y or 0),
                )
        else:
            card = _compose_rank_background(
                resolved_bg_path,
                resolved_bg_mode,
                int(resolved_bg_zoom or 100),
                int(resolved_bg_x or 0),
                int(resolved_bg_y or 0),
            )

        card_w, card_h = card.size
        scale_x = card_w / float(CARD_WIDTH)
        scale_y = card_h / float(CARD_HEIGHT)
        scale = min(scale_x, scale_y)

        draw = ImageDraw.Draw(card)

        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

        avatar_size = max(64, int(AVATAR_SIZE * scale))
        avatar = avatar.resize((avatar_size, avatar_size))

        mask = Image.new("L", (avatar_size, avatar_size), 0)

        mask_draw = ImageDraw.Draw(mask)

        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

        avatar.putalpha(mask)

        avatar_x = int(50 * scale_x)
        avatar_y = int(60 * scale_y)
        card.paste(avatar, (avatar_x, avatar_y), avatar)

        font_big = _safe_truetype(resolved_name_font, int(resolved_name_size * scale))
        font_medium = _safe_truetype(resolved_info_font, int(resolved_info_size * scale))
        font_small = _safe_truetype(resolved_info_font, max(10, int(resolved_info_size * 0.55 * scale)))

        guild_id = getattr(getattr(member, "guild", None), "id", None)

        draw.text((int(260 * scale_x) + resolved_text_x, int(50 * scale_y) + resolved_text_y), member.display_name, font=font_big, fill=resolved_name_color)

        draw.text(
            (int(260 * scale_x) + resolved_text_x, int(120 * scale_y) + resolved_text_y),
            translate("rank.card.level", guild_id=guild_id, level=level),
            font=font_medium,
            fill=resolved_info_color,
        )

        draw.text(
            (int(710 * scale_x) + resolved_text_x, int(140 * scale_y) + resolved_text_y),
            translate("rank.card.xp_progress", guild_id=guild_id, current=xp, needed=needed),
            font=font_small,
            fill=resolved_info_color,
        )

        bar_x = int(260 * scale_x)
        bar_y = int(180 * scale_y)
        bar_width = int(BAR_WIDTH * scale_x)
        bar_height = max(8, int(BAR_HEIGHT * scale_y))

        draw.rectangle(
            (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), fill=(50, 50, 50)
        )

        draw.rectangle(
            (bar_x, bar_y, bar_x + int(bar_width * progress), bar_y + bar_height),
            fill=(140, 110, 255),
        )

        draw.text(
            (int(260 * scale_x) + resolved_text_x, int(220 * scale_y) + resolved_text_y),
            translate("rank.card.messages", guild_id=guild_id, value=messages),
            font=font_small,
            fill=resolved_info_color,
        )

        draw.text(
            (int(450 * scale_x) + resolved_text_x, int(220 * scale_y) + resolved_text_y),
            translate("rank.card.voice", guild_id=guild_id, value=voice_minutes),
            font=font_small,
            fill=resolved_info_color,
        )

        draw.text(
            (int(650 * scale_x) + resolved_text_x, int(220 * scale_y) + resolved_text_y),
            translate("rank.card.achievements", guild_id=guild_id, value=achievements),
            font=font_small,
            fill=resolved_info_color,
        )

        buffer = io.BytesIO()

        card.save(buffer, "PNG")

        buffer.seek(0)

        return discord.File(buffer, filename="rank.png")

    # ======================================================
    # ADMIN COMMANDS
    # ======================================================

    @commands.hybrid_command(description="Addxp command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def addxp(self, ctx, member: discord.Member, amount: int):
        """Add XP using level system."""

        levels = self.bot.get_cog("Levels")

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

    @commands.hybrid_command(description="Removexp command.")
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

    @commands.hybrid_command(description="Reset command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx, member: discord.Member):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)

        user = self.bot.db.get_user(member.id, guild_id=guild_id)

        user["xp"] = 0
        user["level"] = 1
        user["messages"] = 0
        user["voice_time"] = 0
        user["achievements"] = []

        self.bot.db.save(guild_id=guild_id)
        await ctx.send(translate("rank.msg.reset", guild_id=guild_id))


async def setup(bot):

    await bot.add_cog(Rank(bot))
