import discord
import aiohttp
import io
import os
import re

from discord.ext import commands
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


# ==========================================================
# CONFIG
# ==========================================================

WELCOME_CHANNEL_ID = 1471979239367774248
RULES_CHANNEL_ID = 1266609104005103617
ABOUTME_CHANNEL_ID = 1266609208518774794
ROLE_ID = 1472417667670347817

BANNER_PATH = "assets/welcome.png"

FONT_WELCOME = "assets/fonts/Poppins-Bold.ttf"
FONT_USERNAME = "assets/fonts/Poppins-Regular.ttf"


# ==========================================================
# USERNAME CLEAN
# ==========================================================

def clean_username(member: discord.Member):
    """Return a cleaned username without trailing digits or special chars.

    Uses `member.name` (not discriminator). Removes non-allowed chars and
    strips any trailing digits (e.g. "user1234" -> "user").
    """
    name = member.name
    # remove characters we don't want
    name = re.sub(r"[^A-Za-z0-9_. ]", "", name)
    # remove trailing digits (common when users append numbers)
    name = re.sub(r"\d+$", "", name)
    return name.strip()


# ==========================================================
# COG
# ==========================================================

class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    # ======================================================
    # BANNER CREATE
    # ======================================================

    async def create_banner(self, member: discord.Member,
                            top_text: str | None = None) -> discord.File:
        """Create a large welcome banner with the member avatar.

        Layout:
        - background image from `BANNER_PATH`
        - circular avatar centered near the top
        - big "WELCOME" text below avatar
        - username below the welcome text
        """
        try:
            username = clean_username(member)

            async with aiohttp.ClientSession() as session:
                async with session.get(member.display_avatar.url) as resp:
                    avatar_bytes = await resp.read()

            banner = Image.open(BANNER_PATH).convert("RGBA")

            # Scale banner to a very large width so the final image is big
            target_width = 2200
            orig_width, orig_height = banner.size
            if orig_width != target_width:
                ratio = orig_height / orig_width
                banner = banner.resize((target_width, int(target_width * ratio)))
            width, height = banner.size

            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

            # Avatar sizing: keep it proportional to banner width
            avatar_size = min(int(width * 0.24), 720)
            avatar = avatar.resize((avatar_size, avatar_size))

            # Create circular mask and apply
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            avatar.putalpha(mask)

            avatar_x = (width - avatar_size) // 2
            avatar_y = 30
            banner.paste(avatar, (avatar_x, avatar_y), avatar)

            draw = ImageDraw.Draw(banner)

            # Large welcome text (scale with banner width)
            font_welcome = ImageFont.truetype(FONT_WELCOME,
                                              size=max(72, int(width * 0.12)))
            welcome_text = "WELCOME"
            bbox = draw.textbbox((0, 0), welcome_text, font=font_welcome)
            text_width = bbox[2] - bbox[0]
            welcome_x = (width - text_width) // 2
            welcome_y = avatar_y + avatar_size + 18
            draw.text((welcome_x, welcome_y), welcome_text, font=font_welcome,
                      fill=(255, 255, 255))

            # Username below welcome (smaller than welcome) and moved further down
            font_username = ImageFont.truetype(FONT_USERNAME,
                                               size=max(36, int(width * 0.05)))
            bbox_user = draw.textbbox((0, 0), username, font=font_username)
            text_width = bbox_user[2] - bbox_user[0]
            user_x = (width - text_width) // 2
            # place username below the welcome text with extra spacing so it's not
            # hidden by the welcome text
            welcome_height = bbox[3] - bbox[1]
            user_y = welcome_y + welcome_height + int(width * 0.04)
            # ensure username won't overflow bottom
            if user_y + (bbox_user[3] - bbox_user[1]) > height - 40:
                user_y = height - (bbox_user[3] - bbox_user[1]) - 40
            draw.text((user_x, user_y), username, font=font_username,
                      fill=(230, 230, 230))

            # If a top_text is provided, render it centered above the banner
            if top_text:
                # prepare font for the message block
                # scale message font with banner width
                msg_font_size = max(20, int(width * 0.028))

                # Try multiple candidate fonts (assets first, then common system fonts)
                candidates = [
                    os.path.join("assets", "fonts", "aubrey.ttf"),
                ]
                # Windows common font paths
                win_font_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
                candidates += [
                    os.path.join(win_font_dir, p) for p in (
                        "seguisym.ttf",  # Segoe UI Symbol
                        "seguiemj.ttf",  # Segoe UI Emoji
                        "Symbola.ttf",
                        "ArialUnicodeMS.ttf",
                        "arialuni.ttf",
                    )
                ]
                # Linux/mac paths
                candidates += [
                    "/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                ]

                msg_font = None
                for path in candidates:
                    try:
                        if path and os.path.exists(path):
                            msg_font = ImageFont.truetype(path, size=msg_font_size)
                            break
                    except Exception:
                        continue

                if msg_font is None:
                    # final fallback to the configured username font
                    msg_font = ImageFont.truetype(FONT_USERNAME, size=msg_font_size)

                # split lines and measure total height
                lines = top_text.split("\n")
                line_heights = []
                max_line_width = 0
                for line in lines:
                    bbox_line = draw.textbbox((0, 0), line, font=msg_font)
                    w = bbox_line[2] - bbox_line[0]
                    h = bbox_line[3] - bbox_line[1]
                    line_heights.append((w, h))
                    if w > max_line_width:
                        max_line_width = w

                spacing = int(msg_font_size * 0.6)
                top_area_height = sum(h for _, h in line_heights) + spacing * (
                    len(lines) - 1) + 40

                # create new image tall enough for text + banner
                total_height = top_area_height + height
                composite = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))

                # draw text on composite
                draw_comp = ImageDraw.Draw(composite)
                y = 20
                for i, line in enumerate(lines):
                    w, h = line_heights[i]
                    x = (width - w) // 2
                    draw_comp.text((x, y), line, font=msg_font, fill=(255, 255, 255))
                    y += h + spacing

                # paste the original banner below the text
                composite.paste(banner, (0, top_area_height), banner)

                buffer = io.BytesIO()
                composite.save(buffer, format="PNG")
                buffer.seek(0)
                return discord.File(buffer, filename="welcome.png")

            buffer = io.BytesIO()
            banner.save(buffer, format="PNG")
            buffer.seek(0)

            return discord.File(buffer, filename="welcome.png")

        except Exception:
            raise



    # ======================================================
    # JOIN EVENT WITH DEBUG
    # ======================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        print(f"[DEBUG] Join erkannt: {member}")

        guild = member.guild


        welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)

        if welcome_channel is None:

            print("[ERROR] Welcome Channel ist None!")

            return


        print(f"[DEBUG] Welcome Channel gefunden: {welcome_channel.name}")


        rules_channel = guild.get_channel(RULES_CHANNEL_ID)
        aboutme_channel = guild.get_channel(ABOUTME_CHANNEL_ID)


        role = guild.get_role(ROLE_ID)

        if role:

            await member.add_roles(role)

            print("[DEBUG] Rolle vergeben")


        # prepare the exact content message (keeps clickable mentions)
        text = (
            f"{member.mention} 𝗃𝗎𝗌𝗍 𝖼𝗁𝖾𝖼𝗄𝖾𝖽 𝗂𝗇!\n"
            "𝗒𝗈𝗎 𝗆𝖺𝖽𝖾 𝗂𝗍 𝗍𝗈 𝗈𝗎𝗋 𝗅𝗈𝗏𝖾𝗅𝗒 𝖼𝗈𝗆𝗆𝗎𝗇𝗂𝗍𝗒!\n"
            "𝖻𝖾𝖿𝗈𝗋𝖾 𝗒𝗈𝗎 𝖿𝗅𝗈𝖺𝗍 𝖺𝗋𝗈𝗎𝗇𝖽 𝗍𝗁𝖾 𝗌𝖾𝗋𝗏𝖾𝗋, 𝗍𝖺𝗄𝖾 𝖺 𝗌𝖾𝖼 𝗍𝗈 𝗋𝖾𝖺𝖽 𝗍𝗁𝖾 "
            f"{rules_channel.mention}\n\n"
            "˚◟𝗼𝗻𝗰𝗲 𝘆𝗼𝘂 𝗿𝗲𝗮𝗱 𝘁𝗵𝗲 𝗿𝘂𝗹𝗲𝘀◞˚\n\n"
            "❀ 𝘃𝗲𝗿𝗶𝗳𝘆 𝘆𝗼𝘂𝗿𝘀𝗲𝗹𝗳 ❀\n"
            f"𝗁𝖾𝖺𝖽 𝗍𝗈 {rules_channel.mention} ⁠𝗌𝗈 𝗒𝗈𝗎 𝖼𝖺𝗇 𝗎𝗇𝗅𝗈𝖼𝗄 𝗍𝗁𝖾 𝗐𝗁𝗈𝗅𝖾 𝗌𝖾𝗋𝗏𝖾𝗋\n"
            "(𝗒𝖾𝗌, 𝖺𝗅𝗅 𝗍𝗁𝖾 𝖼𝗈𝗓𝗒 & 𝖼𝗁𝖺𝗈𝗍𝗂𝖼 𝗉𝖺𝗋𝗍𝗌)\n\n"
            "❀ 𝗶𝗻𝘁𝗿𝗼𝗱𝘂𝗰𝗲 𝘆𝗼𝘂𝗿𝘀𝗲𝗹𝗳 ❀\n"
            f"𝖼𝗋𝗎𝗂𝖾 𝗈𝗏𝖾𝗋 𝗍𝗈 {aboutme_channel.mention} 𝖺𝗇𝖽 𝗍𝖾𝗅𝗅 𝗎𝗌 𝗆𝗈𝗋𝖾 𝖺𝖻𝗈𝗎𝗍 𝗒𝗈𝗎!\n"
            "𝗐𝖾 𝗐𝖺𝗇𝗍 𝗍𝗈 𝗄𝗇𝗈𝗐 𝗐𝗁𝗈 𝗒𝗈𝗎 𝖺𝗋𝖾 𝖻𝖾𝖿𝗈𝗋𝖾 𝗐𝖾 𝖺𝖽𝗈𝗉𝗍 𝗒𝗈𝗎\n\n"
            "❀ 𝗮𝗳𝘁𝗲𝗿 𝘆𝗼𝘂 𝗵𝗮𝘃𝗲 𝗰𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱 𝗮𝗹𝗹 𝘁𝗵𝗲 𝗳𝗼𝗿𝗺𝗮𝗹𝗶𝘁𝗶𝗲𝘀 ❀\n"
            "𝗀𝗈, 𝗀𝗋𝖺𝖻 𝗒𝗈𝗎𝗋 𝗌𝗇𝖺𝖼𝗄𝗌, 𝗀𝖾𝗍 𝖼𝗈𝗆𝖿𝗒 𝖺𝗇𝖽 𝖾𝗇𝗃𝗈𝗒 𝗍𝗁𝖾 𝗀𝗈𝗈𝖽 𝗏𝗂𝖻𝖾𝗌!"
        )

        # Create a version of the text suitable for rendering into the image
        # Replace mentions with readable names so the image looks clean.
        image_text = text.replace(member.mention, clean_username(member))
        if rules_channel:
            image_text = image_text.replace(rules_channel.mention,
                                            f"#{rules_channel.name}")
        if aboutme_channel:
            image_text = image_text.replace(aboutme_channel.mention,
                                            f"#{aboutme_channel.name}")

        banner = await self.create_banner(member, top_text=image_text)

        # Send only the generated banner image (text already rendered into image)
        await welcome_channel.send(file=banner)


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(Welcome(bot))
