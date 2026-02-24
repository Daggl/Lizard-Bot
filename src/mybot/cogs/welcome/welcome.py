# ==========================================================
# IMPORTS
# ==========================================================

import io
import re
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from mybot.utils.config import load_cog_config

# ==========================================================
# CONFIGURATION (loaded from config/welcome.json with fallbacks)
# ==========================================================


_CFG = load_cog_config("welcome")

VERIFY_CHANNEL_ID = _CFG.get("VERIFY_CHANNEL_ID", 0)
WELCOME_CHANNEL_ID = _CFG.get("WELCOME_CHANNEL_ID", 0)
RULES_CHANNEL_ID = _CFG.get("RULES_CHANNEL_ID", 0)
ABOUTME_CHANNEL_ID = _CFG.get("ABOUTME_CHANNEL_ID", 0)
ROLE_ID = _CFG.get("ROLE_ID", 0)

BANNER_PATH = _CFG.get("BANNER_PATH", "assets/welcome.png")

FONT_WELCOME = _CFG.get("FONT_WELCOME", "assets/fonts/Poppins-Bold.ttf")
# fonts
FONT_USERNAME = _CFG.get("FONT_USERNAME", "assets/fonts/Poppins-Regular.ttf")

# (Using the original hard-coded welcome embed below; no configurable template.)


# ==========================================================
# USERNAME CLEAN FUNCTION
# ==========================================================


def clean_username(member: discord.Member):
    """
    Removes numbers and underscores from the display name
    to generate a clean welcome text.
    """

    name = member.display_name

    name = re.sub(r"\d+", "", name)
    name = re.sub(r"_+", "", name)

    name = name.strip()

    if name == "":
        name = member.name

    return name


# ==========================================================
# COG CLASS
# ==========================================================


class Welcome(commands.Cog):
    """
    Welcome System Cog

    Functions:

    - Create banner
    - Assign role
    - Send welcome message
    - Test command
    """

    def __init__(self, bot):
        self.bot = bot

    # ======================================================
    # BANNER CREATION
    # ======================================================

    async def create_banner(self, member):
        """
        Creates the welcome banner image
        """

        try:

            username = clean_username(member)

            print("[DEBUG] Loading avatar...")

            async with aiohttp.ClientSession() as session:
                async with session.get(member.display_avatar.url) as resp:
                    avatar_bytes = await resp.read()

            print("[DEBUG] Loading banner image...")

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

            draw_mask = ImageDraw.Draw(mask)

            draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)

            avatar.putalpha(mask)

            avatar_y = (height - avatar_size) // 2

            print("[DEBUG] Loading fonts...")

            font_welcome = ImageFont.truetype(FONT_WELCOME, 140)

            font_user_bold = ImageFont.truetype(FONT_WELCOME, 64)

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

            draw.text(
                (welcome_x, welcome_y),
                welcome_text,
                font=font_welcome,
                fill=(255, 255, 255),
            )

            banner.paste(avatar, (avatar_x, avatar_y), avatar)

            bbox_u = draw.textbbox((0, 0), username, font=font_user_bold)

            u_width = bbox_u[2] - bbox_u[0]

            user_x = text_area_x + max(0, (text_area_width - u_width) // 2)

            extra_spacing = 80

            user_y = welcome_y + (bbox_w[3] - bbox_w[1]) + extra_spacing

            draw.text(
                (user_x, user_y), username, font=font_user_bold, fill=(230, 230, 230)
            )

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

            print("[DEBUG] Banner ready")

            return discord.File(buffer, filename="welcome.png")

        except Exception as exc:

            print("[ERROR] Banner Fehler:", exc)

            raise exc

    # ======================================================
    # MEMBER JOIN EVENT
    # ======================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Triggered when a user joins
        """

        print(f"[DEBUG] Join erkannt: {member}")

        guild = member.guild

        welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)

        if welcome_channel is None:

            print("[ERROR] Welcome Channel ist None!")

            return

        print(f"[DEBUG] Welcome Channel gefunden: {welcome_channel.name}")

        rules_channel = guild.get_channel(RULES_CHANNEL_ID)
        aboutme_channel = guild.get_channel(ABOUTME_CHANNEL_ID)
        verify_channel = guild.get_channel(VERIFY_CHANNEL_ID)

        role = guild.get_role(ROLE_ID)

        if role:

            await member.add_roles(role)

            print("[DEBUG] Role assigned")

        banner = await self.create_banner(member)

        print("[DEBUG] Banner erstellt")

        embed = discord.Embed(
            description=(f"""{member.mention} 𝗷𝘂𝘀𝘁 𝗰𝗵𝗲𝗰𝗸𝗲𝗱 𝗶𝗻! 🎔
𝖻𝖾𝖿𝗈𝗋𝖾 𝗒𝗈𝘂 𝖿𝗅𝗈𝖺𝗍 𝖺𝗋𝗈𝗎𝗇𝖽 𝖙𝖍𝖊 𝖘𝖊𝖗𝖛𝖊𝖗,
𝗍𝖺𝗄𝖾 𝖺 𝗌𝖾𝖼 𝗍𝗈 𝗋𝖾𝖺𝖽 𝗍𝗁𝖾 {rules_channel.mention}

˚◟𝗼𝗻𝗰𝗲 𝘆𝗈𝘂 𝗿𝗲𝗮𝘀 𝗍𝗁𝖾 𝗋𝖾𝗅𝖾𝘀◞˚

❀ 𝘃𝗲𝗋𝗂𝗳𝘆 𝘆𝗈𝘂𝗋𝘀𝗲𝗹𝗳 ❀
𝗁𝖾𝖺𝖽 𝗍𝗈 {verify_channel.mention} 𝗌𝗈 𝗒𝗈𝗎 𝖼𝖺𝗇 𝗎𝗇𝗅𝗈𝖼𝗄  𝗍𝗁𝖾 𝗐𝗁𝗈𝗅𝖾 𝗌𝖾𝗋𝗏𝖾𝗋
(𝗒𝖾𝗌, 𝖺𝗅𝗅 𝗍𝗁𝖾 𝖼𝗈𝗓𝗒 & 𝖼𝗁𝖺𝗈𝗍𝗂𝖼 𝗉𝖺𝗋𝗍𝗌)

❀ 𝗶𝗻𝘁𝗋𝗈𝗱𝘂𝗰𝗲 𝘆𝗈𝘂𝗋𝘀𝗲𝗹𝗳 ❀
𝖼𝗋𝗎𝗂𝖼𝗋 𝗈𝗏𝖾𝗋 𝗍𝗈 {aboutme_channel.mention} 𝖺𝗇𝖽 𝗍𝖾𝗅𝗅  𝗎𝗌 𝗆𝗈𝗋𝖾 𝖺𝖻𝗈𝗎𝖳 𝗒𝗈𝗎!
𝗐𝖾 𝗐𝖺𝗇𝗍 𝗍𝗈 𝗄𝗇𝗈𝗐 𝗐𝗁𝗈 𝗒𝗈𝗎 𝖺𝗋𝗂 𝖻𝖾𝖿𝗈𝗋𝖾 𝗐𝖾 𝖺𝖽𝗈𝗉𝗍 𝗒𝗈𝗎

❀ 𝗮𝗳𝘁𝗲𝗋 𝘆𝗈𝘂 𝗁𝗮𝘃𝗘 𝗖𝗈𝗆𝗉𝗅𝗘𝗧𝗘𝗗 𝗔𝗅𝗅 𝗍𝗁𝗘 𝗙𝗈𝗋𝗆𝗔𝗅𝗂𝗍𝗂𝗘𝗌 ❀
𝗀𝗈, 𝗀𝗋𝖺𝖻 𝗒𝗈𝗎𝗋 𝗌𝗇𝖺𝖼𝗄𝗌, 𝗀𝖾𝗍 𝖼𝗈𝗆𝖿𝗒 𝖺𝗇𝖽 𝖾𝗇𝗃𝗈𝗒 𝗍𝗁𝖾 𝗀𝗈𝗈𝖽 𝗏𝗂𝖻𝖾𝗌!
"""),
            color=discord.Color.from_rgb(140, 110, 255),
            timestamp=datetime.utcnow(),
        )

        embed.set_image(url="attachment://welcome.png")

        print("[DEBUG] Sending message...")

        await welcome_channel.send(file=banner, embed=embed)

        print("[DEBUG] Message sent")

    # ======================================================
    # TEST COMMAND
    # ======================================================

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def testwelcome(self, ctx):

        print("[DEBUG] Test Command benutzt")

        await self.on_member_join(ctx.author)


# ==========================================================
# SETUP FUNCTION
# ==========================================================


async def setup(bot):

    await bot.add_cog(Welcome(bot))
