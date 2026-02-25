"""Welcome cog: uses config/welcome.json as source of truth.

If `WELCOME_MESSAGE` is missing from the config the cog sends the banner only.
"""

from typing import Optional

import io
import re
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from mybot.utils.config import clear_cog_config_cache, load_cog_config
import sys


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


def _load_welcome_cfg() -> dict:
    try:
        clear_cog_config_cache("welcome")
    except Exception:
        pass
    try:
        return load_cog_config("welcome") or {}
    except Exception:
        return {}


def _safe_truetype(path: Optional[str], size: int):
    try:
        if path:
            return ImageFont.truetype(path, size)
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


def clean_username(member: discord.Member) -> str:
    name = member.display_name
    name = re.sub(r"\d+", "", name)
    name = re.sub(r"_+", "", name)
    name = name.strip() or member.name
    return name


class Welcome(commands.Cog):
    """Welcome cog: generates banner and posts welcome based on config."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_banner(self, member: discord.Member, overrides: Optional[dict] = None) -> discord.File:
        """Generate the welcome banner image."""
        cfg = _load_welcome_cfg()
        if isinstance(overrides, dict):
            cfg = {**cfg, **overrides}

        banner_path = cfg.get("BANNER_PATH", "assets/welcome.png")
        font_welcome_path = cfg.get("FONT_WELCOME", "assets/fonts/Poppins-Bold.ttf")
        font_username_path = cfg.get("FONT_USERNAME", "assets/fonts/Poppins-Regular.ttf")
        banner_title = str(cfg.get("BANNER_TITLE", "WELCOME") or "WELCOME")
        offset_x = int(cfg.get("OFFSET_X", 0) or 0)
        offset_y = int(cfg.get("OFFSET_Y", 0) or 0)
        title_font_size = int(cfg.get("TITLE_FONT_SIZE", 140) or 140)
        username_font_size = int(cfg.get("USERNAME_FONT_SIZE", 64) or 64)
        title_color = _parse_hex_color(cfg.get("TITLE_COLOR", "#FFFFFF"), (255, 255, 255))
        username_color = _parse_hex_color(cfg.get("USERNAME_COLOR", "#E6E6E6"), (230, 230, 230))
        title_offset_x = int(cfg.get("TITLE_OFFSET_X", 0) or 0)
        title_offset_y = int(cfg.get("TITLE_OFFSET_Y", 0) or 0)
        username_offset_x = int(cfg.get("USERNAME_OFFSET_X", 0) or 0)
        username_offset_y = int(cfg.get("USERNAME_OFFSET_Y", 0) or 0)
        text_offset_x = int(cfg.get("TEXT_OFFSET_X", 0) or 0)
        text_offset_y = int(cfg.get("TEXT_OFFSET_Y", 0) or 0)

        username = clean_username(member)

        safe_print("[DEBUG] Loading avatar...")
        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

        safe_print("[DEBUG] Loading banner image...")
        try:
            banner = Image.open(banner_path).convert("RGBA")
            width, height = banner.size
        except Exception:
            width, height = 1400, 420
            banner = Image.new("RGBA", (width, height), (18, 18, 18, 255))

        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        margin = 40
        avatar_size = min(360, height - margin * 2)
        avatar = avatar.resize((avatar_size, avatar_size))

        mask = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar.putalpha(mask)

        avatar_base_x = margin
        avatar_base_y = (height - avatar_size) // 2
        avatar_y = avatar_base_y + offset_y

        font_welcome = _safe_truetype(font_welcome_path, max(8, title_font_size))
        font_user = _safe_truetype(font_username_path, max(8, username_font_size))

        draw = ImageDraw.Draw(banner)
        welcome_text = banner_title
        bbox_w = draw.textbbox((0, 0), welcome_text, font=font_welcome)
        w_width = bbox_w[2] - bbox_w[0]

        spacing = 40
        # Keep avatar position independent from title font size.
        avatar_x = avatar_base_x + offset_x

        # Keep text area independent from avatar offsets.
        text_area_x = avatar_base_x + avatar_size + spacing
        text_area_width = width - text_area_x - margin
        welcome_x = text_area_x + max(0, (text_area_width - w_width) // 2)
        welcome_y = avatar_base_y + 40
        welcome_x += text_offset_x
        welcome_y += text_offset_y
        welcome_x += title_offset_x
        welcome_y += title_offset_y

        draw.text((welcome_x, welcome_y), welcome_text, font=font_welcome, fill=title_color)
        banner.paste(avatar, (avatar_x, avatar_y), avatar)

        bbox_u = draw.textbbox((0, 0), username, font=font_user)
        u_width = bbox_u[2] - bbox_u[0]
        user_x = text_area_x + max(0, (text_area_width - u_width) // 2)
        # Keep username baseline independent from title font size.
        user_y = avatar_base_y + 220
        user_x += text_offset_x
        user_y += text_offset_y
        user_x += username_offset_x
        user_y += username_offset_y
        draw.text((user_x, user_y), username, font=font_user, fill=username_color)

        if banner.mode == "RGBA":
            background_rgb = Image.new("RGB", banner.size, (18, 18, 18))
            alpha = banner.split()[3]
            background_rgb.paste(banner, mask=alpha)
            final_image = background_rgb
        else:
            final_image = banner.convert("RGB")

        buffer = io.BytesIO()
        final_image.save(buffer, "PNG")
        buffer.seek(0)
        safe_print("[DEBUG] Banner ready")
        return discord.File(buffer, filename="welcome.png")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = _load_welcome_cfg()
        verify_channel_id = cfg.get("VERIFY_CHANNEL_ID", 0)
        welcome_channel_id = cfg.get("WELCOME_CHANNEL_ID", 0)
        rules_channel_id = cfg.get("RULES_CHANNEL_ID", 0)
        aboutme_channel_id = cfg.get("ABOUTME_CHANNEL_ID", 0)
        role_id = cfg.get("ROLE_ID", 0)
        welcome_message: Optional[str] = cfg.get("WELCOME_MESSAGE")

        safe_print(f"[DEBUG] Join erkannt: {member}")
        guild = member.guild
        welcome_channel = guild.get_channel(welcome_channel_id)
        if welcome_channel is None:
            safe_print("[ERROR] Welcome Channel ist None!")
            return

        safe_print(f"[DEBUG] Welcome Channel gefunden: {welcome_channel.name}")

        rules_channel = guild.get_channel(rules_channel_id)
        aboutme_channel = guild.get_channel(aboutme_channel_id)
        verify_channel = guild.get_channel(verify_channel_id)
        role = guild.get_role(role_id)
        if role:
            await member.add_roles(role)
            safe_print("[DEBUG] Role assigned")

        banner = await self.create_banner(member)
        safe_print("[DEBUG] Banner erstellt")

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

        embed = discord.Embed(description=description, color=discord.Color.from_rgb(140, 110, 255), timestamp=datetime.utcnow())
        embed.set_image(url="attachment://welcome.png")
        safe_print("[DEBUG] Sending message...")
        await welcome_channel.send(file=banner, embed=embed)
        safe_print("[DEBUG] Message sent")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def testwelcome(self, ctx: commands.Context):
        safe_print("[DEBUG] Test Command benutzt")
        await self.on_member_join(ctx.author)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
