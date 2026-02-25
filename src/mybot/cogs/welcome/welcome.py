"""Welcome cog: uses the canonical `WELCOME_MESSAGE` from config/welcome.json.

This version deliberately does NOT include an in-code default template.
If `WELCOME_MESSAGE` is missing from the config the cog will send the
banner image only (no fallback text).
"""

from typing import Optional

import io
import re
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from mybot.utils.config import load_cog_config
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


_CFG = load_cog_config("welcome")

VERIFY_CHANNEL_ID = _CFG.get("VERIFY_CHANNEL_ID", 0)
WELCOME_CHANNEL_ID = _CFG.get("WELCOME_CHANNEL_ID", 0)
RULES_CHANNEL_ID = _CFG.get("RULES_CHANNEL_ID", 0)
ABOUTME_CHANNEL_ID = _CFG.get("ABOUTME_CHANNEL_ID", 0)
ROLE_ID = _CFG.get("ROLE_ID", 0)

BANNER_PATH = _CFG.get("BANNER_PATH", "assets/welcome.png")

FONT_WELCOME = _CFG.get("FONT_WELCOME", "assets/fonts/Poppins-Bold.ttf")
FONT_USERNAME = _CFG.get("FONT_USERNAME", "assets/fonts/Poppins-Regular.ttf")

# Only read the message from config; do NOT provide a built-in default.
WELCOME_MESSAGE: Optional[str] = _CFG.get("WELCOME_MESSAGE")


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

    async def create_banner(self, member: discord.Member) -> discord.File:
        """Generate the welcome banner image."""
        username = clean_username(member)

        safe_print("[DEBUG] Loading avatar...")
        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

        safe_print("[DEBUG] Loading banner image...")
        try:
            banner = Image.open(BANNER_PATH).convert("RGBA")
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

        avatar_y = (height - avatar_size) // 2

        font_welcome = ImageFont.truetype(FONT_WELCOME, 140) if FONT_WELCOME else ImageFont.load_default()
        font_user = ImageFont.truetype(FONT_WELCOME, 64) if FONT_WELCOME else ImageFont.load_default()

        draw = ImageDraw.Draw(banner)
        welcome_text = "WELCOME"
        bbox_w = draw.textbbox((0, 0), welcome_text, font=font_welcome)
        w_width = bbox_w[2] - bbox_w[0]

        S = 40
        avatar_x_calc = int((width - avatar_size - S + margin - w_width) / 3)
        avatar_x = max(margin, avatar_x_calc)

        text_area_x = avatar_x + avatar_size + S
        text_area_width = width - text_area_x - margin
        welcome_x = text_area_x + max(0, (text_area_width - w_width) // 2)
        welcome_y = avatar_y + 40

        draw.text((welcome_x, welcome_y), welcome_text, font=font_welcome, fill=(255, 255, 255))
        banner.paste(avatar, (avatar_x, avatar_y), avatar)

        bbox_u = draw.textbbox((0, 0), username, font=font_user)
        u_width = bbox_u[2] - bbox_u[0]
        user_x = text_area_x + max(0, (text_area_width - u_width) // 2)
        extra_spacing = 80
        user_y = welcome_y + (bbox_w[3] - bbox_w[1]) + extra_spacing
        draw.text((user_x, user_y), username, font=font_user, fill=(230, 230, 230))

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
        safe_print(f"[DEBUG] Join erkannt: {member}")
        guild = member.guild
        welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel is None:
            safe_print("[ERROR] Welcome Channel ist None!")
            return

        safe_print(f"[DEBUG] Welcome Channel gefunden: {welcome_channel.name}")

        rules_channel = guild.get_channel(RULES_CHANNEL_ID)
        aboutme_channel = guild.get_channel(ABOUTME_CHANNEL_ID)
        verify_channel = guild.get_channel(VERIFY_CHANNEL_ID)
        role = guild.get_role(ROLE_ID)
        if role:
            await member.add_roles(role)
            safe_print("[DEBUG] Role assigned")

        banner = await self.create_banner(member)
        safe_print("[DEBUG] Banner erstellt")

        # If no WELCOME_MESSAGE configured, do not use a built-in default.
        if not WELCOME_MESSAGE:
            safe_print("[WARN] No WELCOME_MESSAGE configured; sending banner only.")
            await welcome_channel.send(file=banner)
            return

        # prepare placeholders
        rules_mention = rules_channel.mention if rules_channel is not None else "#rules"
        verify_mention = verify_channel.mention if verify_channel is not None else "#verify"
        aboutme_mention = aboutme_channel.mention if aboutme_channel is not None else "#aboutme"

        try:
            description = WELCOME_MESSAGE.format(
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
