"""Welcome cog: uses config/welcome.json as source of truth.

If `WELCOME_MESSAGE` is missing from the config the cog sends the banner only.
"""

import io
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from mybot.utils.config import clear_cog_config_cache, load_cog_config
from mybot.utils.paths import REPO_ROOT


def safe_print(*args, **kwargs):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_args = []
    for a in args:
        s = str(a)
        try:
            s.encode(encoding)
            safe_args.append(s)
        except Exception:
            safe_args.append(s.encode(encoding, errors="replace").decode(encoding))
    print(*safe_args, **kwargs)


def _debug(*args, **kwargs):
    if str(os.environ.get("MYBOT_DEBUG_WELCOME", "")).strip().lower() in {"1", "true", "yes", "on"}:
        safe_print(*args, **kwargs)


def _load_welcome_cfg(guild_id: int | str | None = None) -> dict:
    try:
        clear_cog_config_cache("welcome")
    except Exception:
        pass
    try:
        return load_cog_config("welcome", guild_id=guild_id) or {}
    except Exception:
        return {}


def _safe_truetype(path: Optional[str], size: int):
    try:
        resolved = path
        if path and not os.path.isabs(path):
            resolved = os.path.join(REPO_ROOT, path)
        if resolved and os.path.exists(resolved):
            return ImageFont.truetype(resolved, size)
    except Exception:
        pass
    return ImageFont.load_default()


def _parse_hex_color(value: Optional[str], fallback: tuple[int, int, int]) -> tuple[int, int, int]:
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


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    val = _to_int(value, default)
    return max(minimum, min(maximum, val))


def _compose_background(
    image_path: str,
    width: int,
    height: int,
    mode: str,
    zoom_percent: int,
    offset_x: int,
    offset_y: int,
) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (18, 18, 18, 255))
    try:
        if not image_path or not os.path.exists(image_path):
            return canvas
        src = Image.open(image_path).convert("RGBA")
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

    resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)

    if mode_norm == "stretch":
        stretched = src.resize((width, height), resampling)
        canvas.paste(stretched, (0, 0), stretched)
        return canvas

    if mode_norm == "cover":
        base_scale = max(width / float(src_w), height / float(src_h))
    else:
        base_scale = min(width / float(src_w), height / float(src_h))

    scale = base_scale * (zoom / 100.0)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    fitted = src.resize((new_w, new_h), resampling)

    x = (width - new_w) // 2 + int(offset_x or 0)
    y = (height - new_h) // 2 + int(offset_y or 0)
    canvas.paste(fitted, (x, y), fitted)
    return canvas


def clean_username(member: discord.Member) -> str:
    name = member.display_name
    name = re.sub(r"\d+", "", name)
    name = re.sub(r"_+", "", name)
    name = name.strip() or member.name
    return name


# ======================================================
# STANDALONE RENDER FUNCTION - for UI preview and bot usage
# ======================================================


def render_welcome_banner(
    banner_path: str,
    username: str = "NewMember",
    title: str = "WELCOME",
    avatar_bytes: Optional[bytes] = None,
    bg_mode: str = "cover",
    bg_zoom: int = 100,
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
    title_font_size: int = 140,
    username_font_size: int = 64,
    title_color: str = "#FFFFFF",
    username_color: str = "#E6E6E6",
    offset_x: int = 0,
    offset_y: int = 0,
    title_offset_x: int = 0,
    title_offset_y: int = 0,
    username_offset_x: int = 0,
    username_offset_y: int = 0,
    text_offset_x: int = 0,
    text_offset_y: int = 0,
    avatar_size: int = 360,
    font_welcome_path: str = "assets/fonts/Poppins-Bold.ttf",
    font_username_path: str = "assets/fonts/Poppins-Regular.ttf",
) -> bytes:
    """
    Pure rendering function for welcome banner.
    Returns PNG bytes. Can be used by UI preview or bot.
    """
    width, height = 1500, 550
    username = str(username or "NewMember")
    title = str(title or "WELCOME")
    avatar_size = _clamp_int(avatar_size, 16, 2000, 360)

    # Resolve banner path
    if banner_path and not os.path.isabs(banner_path):
        banner_path = os.path.join(REPO_ROOT, banner_path)

    default_banner_abs = os.path.abspath(os.path.join(REPO_ROOT, "assets", "welcome.png"))
    requested_banner_abs = os.path.abspath(banner_path) if banner_path else ""

    # Use default banner as-is, otherwise compose background
    if requested_banner_abs.lower() == default_banner_abs.lower() and os.path.exists(requested_banner_abs):
        try:
            banner = Image.open(requested_banner_abs).convert("RGBA")
            width, height = banner.size
        except Exception:
            banner = Image.new("RGBA", (width, height), (18, 18, 18, 255))
    else:
        banner = _compose_background(
            banner_path, width, height, bg_mode, bg_zoom, bg_offset_x, bg_offset_y
        )

    draw = ImageDraw.Draw(banner)
    margin = 40
    actual_avatar_size = max(16, min(avatar_size, height - margin * 2))

    # Load avatar
    if avatar_bytes:
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        except Exception:
            avatar = Image.new("RGBA", (actual_avatar_size, actual_avatar_size), (100, 100, 100, 255))
    else:
        avatar = Image.new("RGBA", (actual_avatar_size, actual_avatar_size), (100, 100, 100, 255))

    avatar = avatar.resize((actual_avatar_size, actual_avatar_size))

    # Circular mask
    mask = Image.new("L", (actual_avatar_size, actual_avatar_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, actual_avatar_size, actual_avatar_size), fill=255)
    avatar.putalpha(mask)

    # Positions
    avatar_base_x = margin
    avatar_base_y = (height - actual_avatar_size) // 2
    avatar_x = avatar_base_x + offset_x
    avatar_y = avatar_base_y + offset_y

    # Fonts
    font_welcome = _safe_truetype(font_welcome_path, max(8, title_font_size))
    font_user = _safe_truetype(font_username_path, max(8, username_font_size))

    # Title position
    title_parsed_color = _parse_hex_color(title_color, (255, 255, 255))
    username_parsed_color = _parse_hex_color(username_color, (230, 230, 230))

    bbox_w = draw.textbbox((0, 0), title, font=font_welcome)
    w_width = bbox_w[2] - bbox_w[0]

    spacing = 40
    text_area_x = avatar_base_x + actual_avatar_size + spacing
    text_area_width = width - text_area_x - margin
    welcome_x = text_area_x + max(0, (text_area_width - w_width) // 2)
    welcome_y = avatar_base_y + 40
    welcome_x += text_offset_x + title_offset_x
    welcome_y += text_offset_y + title_offset_y

    draw.text((welcome_x, welcome_y), title, font=font_welcome, fill=title_parsed_color)
    banner.paste(avatar, (avatar_x, avatar_y), avatar)

    # Username position
    bbox_u = draw.textbbox((0, 0), username, font=font_user)
    u_width = bbox_u[2] - bbox_u[0]
    user_x = text_area_x + max(0, (text_area_width - u_width) // 2)
    user_y = avatar_base_y + 220
    user_x += text_offset_x + username_offset_x
    user_y += text_offset_y + username_offset_y

    draw.text((user_x, user_y), username, font=font_user, fill=username_parsed_color)

    # Convert to RGB for PNG
    if banner.mode == "RGBA":
        background_rgb = Image.new("RGB", banner.size, (18, 18, 18))
        alpha = banner.split()[3]
        background_rgb.paste(banner, mask=alpha)
        final_image = background_rgb
    else:
        final_image = banner.convert("RGB")

    buffer = io.BytesIO()
    final_image.save(buffer, "PNG")
    return buffer.getvalue()


class Welcome(commands.Cog):
    """Welcome cog: generates banner and posts welcome based on config."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_banner(self, member: discord.Member, overrides: Optional[dict] = None) -> discord.File:
        """Generate the welcome banner image using shared renderer."""
        guild_id = getattr(getattr(member, 'guild', None), 'id', None)
        cfg = _load_welcome_cfg(guild_id=guild_id)
        if isinstance(overrides, dict):
            cfg = {**cfg, **overrides}

        username = clean_username(member)

        _debug("[DEBUG] Loading avatar...")
        avatar_bytes: bytes | None = None
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(member.display_avatar.url) as resp:
                    if resp.status == 200:
                        avatar_bytes = await resp.read()
        except Exception:
            avatar_bytes = None

        _debug("[DEBUG] Rendering banner...")
        png_bytes = render_welcome_banner(
            banner_path=cfg.get("BANNER_PATH", "assets/welcome.png"),
            username=username,
            title=str(cfg.get("BANNER_TITLE", "WELCOME") or "WELCOME"),
            avatar_bytes=avatar_bytes,
            bg_mode=str(cfg.get("BG_MODE", "cover") or "cover"),
            bg_zoom=int(cfg.get("BG_ZOOM", 100) or 100),
            bg_offset_x=int(cfg.get("BG_OFFSET_X", 0) or 0),
            bg_offset_y=int(cfg.get("BG_OFFSET_Y", 0) or 0),
            title_font_size=int(cfg.get("TITLE_FONT_SIZE", 140) or 140),
            username_font_size=int(cfg.get("USERNAME_FONT_SIZE", 64) or 64),
            title_color=cfg.get("TITLE_COLOR", "#FFFFFF"),
            username_color=cfg.get("USERNAME_COLOR", "#E6E6E6"),
            offset_x=int(cfg.get("OFFSET_X", 0) or 0),
            offset_y=int(cfg.get("OFFSET_Y", 0) or 0),
            title_offset_x=int(cfg.get("TITLE_OFFSET_X", 0) or 0),
            title_offset_y=int(cfg.get("TITLE_OFFSET_Y", 0) or 0),
            username_offset_x=int(cfg.get("USERNAME_OFFSET_X", 0) or 0),
            username_offset_y=int(cfg.get("USERNAME_OFFSET_Y", 0) or 0),
            text_offset_x=int(cfg.get("TEXT_OFFSET_X", 0) or 0),
            text_offset_y=int(cfg.get("TEXT_OFFSET_Y", 0) or 0),
            avatar_size=int(cfg.get("AVATAR_SIZE", 360) or 360),
            font_welcome_path=cfg.get("FONT_WELCOME", "assets/fonts/Poppins-Bold.ttf"),
            font_username_path=cfg.get("FONT_USERNAME", "assets/fonts/Poppins-Regular.ttf"),
        )

        _debug("[DEBUG] Banner ready")
        return discord.File(io.BytesIO(png_bytes), filename="welcome.png")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = getattr(getattr(member, 'guild', None), 'id', None)
        cfg = _load_welcome_cfg(guild_id=guild_id)
        verify_channel_id = int(cfg.get("VERIFY_CHANNEL_ID", 0) or 0)
        welcome_channel_id = int(cfg.get("WELCOME_CHANNEL_ID", 0) or 0)
        rules_channel_id = int(cfg.get("RULES_CHANNEL_ID", 0) or 0)
        aboutme_channel_id = int(cfg.get("ABOUTME_CHANNEL_ID", 0) or 0)
        role_id = int(cfg.get("ROLE_ID", 0) or 0)
        welcome_message: Optional[str] = cfg.get("WELCOME_MESSAGE")

        _debug(f"[DEBUG] Member join detected: {member}")
        guild = member.guild
        welcome_channel = guild.get_channel(welcome_channel_id)
        if welcome_channel is None:
            safe_print("[ERROR] Welcome channel is None!")
            return

        _debug(f"[DEBUG] Welcome channel found: {welcome_channel.name}")

        rules_channel = guild.get_channel(rules_channel_id)
        aboutme_channel = guild.get_channel(aboutme_channel_id)
        verify_channel = guild.get_channel(verify_channel_id)
        role = guild.get_role(role_id)
        if role:
            await member.add_roles(role)
            _debug("[DEBUG] Role assigned")

        banner = await self.create_banner(member)
        _debug("[DEBUG] Banner created")

        if not welcome_message:
            safe_print("[WARN] No WELCOME_MESSAGE configured; sending banner only.")
            await welcome_channel.send(file=banner)
            return

        rules_mention = rules_channel.mention if rules_channel is not None else "#rules"
        verify_mention = verify_channel.mention if verify_channel is not None else "#verify"
        aboutme_mention = aboutme_channel.mention if aboutme_channel is not None else "#aboutme"

        try:
            description = welcome_message.format(
                mention=member.mention,
                rules_channel=rules_mention,
                verify_channel=verify_mention,
                aboutme_channel=aboutme_mention,
            )
        except Exception:
            safe_print("[ERROR] Failed formatting WELCOME_MESSAGE; sending banner only.")
            await welcome_channel.send(file=banner)
            return

        embed = discord.Embed(description=description, color=discord.Color.from_rgb(140, 110, 255), timestamp=datetime.now(timezone.utc))
        embed.set_image(url="attachment://welcome.png")
        _debug("[DEBUG] Sending message...")
        await welcome_channel.send(file=banner, embed=embed)
        _debug("[DEBUG] Message sent")

    @commands.hybrid_command(description="Testwelcome command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testwelcome(self, ctx: commands.Context):
        _debug("[DEBUG] Test command used")
        member = ctx.author
        guild_id = getattr(getattr(member, 'guild', None), 'id', None)
        cfg = _load_welcome_cfg(guild_id=guild_id)

        # Determine target channel: test override > ctx.channel
        override = getattr(self.bot, "_ui_test_channel_override", None)
        target_channel = override or ctx.channel

        welcome_channel_id = int(cfg.get("WELCOME_CHANNEL_ID", 0) or 0)
        rules_channel_id = int(cfg.get("RULES_CHANNEL_ID", 0) or 0)
        aboutme_channel_id = int(cfg.get("ABOUTME_CHANNEL_ID", 0) or 0)
        verify_channel_id = int(cfg.get("VERIFY_CHANNEL_ID", 0) or 0)
        welcome_message: Optional[str] = cfg.get("WELCOME_MESSAGE")

        guild = member.guild
        rules_channel = guild.get_channel(rules_channel_id) if guild else None
        aboutme_channel = guild.get_channel(aboutme_channel_id) if guild else None
        verify_channel = guild.get_channel(verify_channel_id) if guild else None

        banner = await self.create_banner(member)
        _debug("[DEBUG] Banner created")

        if not welcome_message:
            await target_channel.send(file=banner)
            return

        rules_mention = rules_channel.mention if rules_channel is not None else "#rules"
        verify_mention = verify_channel.mention if verify_channel is not None else "#verify"
        aboutme_mention = aboutme_channel.mention if aboutme_channel is not None else "#aboutme"

        try:
            description = welcome_message.format(
                mention=member.mention,
                rules_channel=rules_mention,
                verify_channel=verify_mention,
                aboutme_channel=aboutme_mention,
            )
        except Exception:
            await target_channel.send(file=banner)
            return

        embed = discord.Embed(
            description=description,
            color=discord.Color.from_rgb(140, 110, 255),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_image(url="attachment://welcome.png")
        _debug("[DEBUG] Sending test welcome message...")
        await target_channel.send(file=banner, embed=embed)
        _debug("[DEBUG] Test welcome message sent")


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
